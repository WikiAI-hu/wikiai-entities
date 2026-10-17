<?php
/**
 * WikiAI HFCM consistency watchdog v1.0.0
 *
 * Checks active HFCM assignments and WordPress post modifications every
 * 15 minutes using WP-Cron. Never edits HFCM snippets, source posts or JSON-LD.
 * Rebuilds stale /entity/{slug}.html only after checking the source.
 * First run establishes a non-destructive baseline.
 */

if ( ! defined( 'ABSPATH' ) ) { return; }

add_filter( 'cron_schedules', static function ( $schedules ) {
    $schedules['wikiai_hfcm_15min'] = array(
        'interval' => 15 * MINUTE_IN_SECONDS,
        'display'  => 'WikiAI HFCM consistency check (15 minutes)',
    );
    return $schedules;
} );

add_action( 'init', static function () {
    if ( ! wp_next_scheduled( 'wikiai_hfcm_watchdog_tick' ) ) {
        wp_schedule_event( time() + 120, 'wikiai_hfcm_15min', 'wikiai_hfcm_watchdog_tick' );
    }
}, 30 );

function wikiai_hfcm_watchdog_run( $force_id = 0, $force = false ) {
    if ( get_transient( 'wikiai_hfcm_watchdog_busy_v1' ) ) {
        return new WP_Error( 'wikiai_hfcm_watchdog_busy', 'An audit is already running.', array( 'status' => 409 ) );
    }

    set_transient( 'wikiai_hfcm_watchdog_busy_v1', 1, 4 * MINUTE_IN_SECONDS );

    try {
        global $wpdb;

        if ( ! function_exists( 'wikiai_hfcm_auto_parse_posts' ) ||
             ! function_exists( 'wikiai_hfcm_auto_generate' ) ) {
            throw new RuntimeException( 'WikiAI HFCM auto-regenerator #117 is not active.' );
        }

        $table = $wpdb->prefix . 'hfcm_scripts';
        $rows = $wpdb->get_results(
            "SELECT script_id, status, display_on, s_posts, MD5(snippet) AS content_hash
             FROM {$table} ORDER BY script_id ASC",
            ARRAY_A
        );

        if ( null === $rows || '' !== $wpdb->last_error ) {
            throw new RuntimeException( 'Unable to inspect HFCM fingerprints.' );
        }

        $posts = get_posts( array(
            'post_type'      => 'post',
            'post_status'    => 'publish',
            'category'       => 8,
            'posts_per_page' => -1,
            'fields'         => 'ids',
            'exclude'        => array( 637 ),
        ) );

        if ( ! is_array( $posts ) || count( $posts ) < 10 ) {
            throw new RuntimeException( 'Unexpectedly incomplete business inventory.' );
        }

        $posted = array_fill_keys( array_map( 'intval', $posts ), true );
        $sources = array_fill_keys( array_keys( $posted ), array() );

        foreach ( $rows as $row ) {
            if ( ! in_array( $row['status'], array( 'active', '1' ), true ) ) {
                continue;
            }
            $id = absint( $row['script_id'] );
            if ( ! $id ) { continue; }

            foreach ( wikiai_hfcm_auto_parse_posts( $row['s_posts'] ) as $post_id ) {
                if ( isset( $posted[ $post_id ] ) ) {
                    $sources[ $post_id ][] = $id . ':' . (string) $row['content_hash'];
                }
            }
        }

        $old = get_option( 'wikiai_hfcm_watchdog_hashes_v1', null );
        $first_run = ! is_array( $old );
        $hashes = $first_run ? array() : $old;
        $report = array(
            'version' => '1.0.0',
            'time_utc' => current_time( 'mysql', true ),
            'first_run' => $first_run,
            'checked' => 0,
            'baselined' => 0,
            'regenerated' => array(),
            'skipped' => array(),
            'errors' => array(),
        );

        foreach ( array_keys( $posted ) as $post_id ) {
            $report['checked']++;
            sort( $sources[ $post_id ], SORT_STRING );
            $updated = (string) get_post_field( 'post_modified_gmt', $post_id );
            $fingerprint = hash( 'sha256', $updated . '|' . implode( ';', $sources[ $post_id ] ) );
            $old_hash = isset( $hashes[ $post_id ] ) ? (string) $hashes[ $post_id ] : '';

            // Do not silently replace a rich machine record on initial rollout.
            if ( $first_run && ! ( $force && (int) $force_id === (int) $post_id ) ) {
                $hashes[ $post_id ] = $fingerprint;
                $report['baselined']++;
                continue;
            }

            $changed = $force && (int) $force_id === (int) $post_id ||
                       '' === $old_hash || ! hash_equals( $old_hash, $fingerprint );

            if ( ! $changed ) {
                continue;
            }

            if ( empty( $sources[ $post_id ] ) ) {
                $report['errors'][ (string) $post_id ] = 'No active post-specific HFCM source; snapshot preserved.';
                continue;
            }

            $relative = 'entity/' . get_post_field( 'post_name', $post_id ) . '.html';
            $file = trailingslashit( ABSPATH ) . $relative;
            $previous = is_file( $file ) ? @file_get_contents( $file ) : null;
            $old_size = is_string( $previous ) ? strlen( $previous ) : 0;

            $result = wikiai_hfcm_auto_generate( $post_id );
            if ( empty( $result['ok'] ) ) {
                $report['errors'][ (string) $post_id ] =
                    isset( $result['error'] ) ? (string) $result['error'] : 'Failed to regenerate machine HTML.';
                continue;
            }

            clearstatcache( true, $file );
            $new_size = is_file( $file ) ? (int) filesize( $file ) : 0;

            if ( $new_size < 10000 || ( $old_size >= 40000 && $new_size < $old_size * 0.5 ) ) {
                // Revert suspicious, destructive re-generation. Keep previous checksum.
                if ( is_string( $previous ) ) {
                    $restore = $file . '.rollback-' . wp_generate_password( 8, false, false );
                    if ( false !== @file_put_contents( $restore, $previous, LOCK_EX ) ) {
                        @chmod( $restore, 0644 );
                        @rename( $restore, $file );
                    } else {
                        @unlink( $restore );
                    }
                }
                $report['errors'][ (string) $post_id ] =
                    sprintf( 'Suspicious machine snapshot size: %d -> %d bytes; previous HTML preserved when available.',
                             $old_size, $new_size );
                continue;
            }

            $hashes[ $post_id ] = $fingerprint;
            $report['regenerated'][] = array(
                'post_id' => $post_id,
                'source' => $result['source'] ?? 'unknown',
                'bytes' => $new_size,
                'url' => home_url( '/' . $relative ),
            );

            // If WP Super Cache is installed, evict the stale profile page.
            if ( function_exists( 'wp_cache_post_change' ) ) {
                wp_cache_post_change( $post_id );
            } else {
                clean_post_cache( $post_id );
            }

            // Avoid a long cron callback if many profiles changed at once.
            if ( count( $report['regenerated'] ) >= 8 ) {
                $report['skipped'][] = 'More changes remain for the next 15-minute run.';
                break;
            }
        }

        // A deleted company must not be kept in the active checksum inventory.
        $allowed = array_map( 'strval', array_keys( $posted ) );
        $hashes = array_intersect_key( $hashes, array_fill_keys( $allowed, true ) );
        update_option( 'wikiai_hfcm_watchdog_hashes_v1', $hashes, false );
        update_option( 'wikiai_hfcm_watchdog_status_v1', $report, false );
        return $report;
    } catch ( Throwable $error ) {
        $report = array(
            'version' => '1.0.0',
            'time_utc' => current_time( 'mysql', true ),
            'fatal_error' => $error->getMessage(),
        );
        update_option( 'wikiai_hfcm_watchdog_status_v1', $report, false );
        return new WP_Error( 'wikiai_hfcm_watchdog_failed',
            $error->getMessage(), array( 'status' => 500 ) );
    } finally {
        delete_transient( 'wikiai_hfcm_watchdog_busy_v1' );
    }
}

add_action( 'wikiai_hfcm_watchdog_tick', static function () {
    wikiai_hfcm_watchdog_run();
} );

add_action( 'rest_api_init', static function () {
    $permission = static function () { return current_user_can( 'manage_options' ); };
    register_rest_route( 'wikiai-hfcm-watchdog/v1', '/status', array(
        'methods' => WP_REST_Server::READABLE,
        'permission_callback' => $permission,
        'callback' => static function () {
            return rest_ensure_response( array(
                'active' => true,
                'next_run' => wp_next_scheduled( 'wikiai_hfcm_watchdog_tick' ),
                'status' => get_option( 'wikiai_hfcm_watchdog_status_v1', array() ),
                'tracked' => count( (array) get_option( 'wikiai_hfcm_watchdog_hashes_v1', array() ) ),
            ) );
        },
    ) );
    register_rest_route( 'wikiai-hfcm-watchdog/v1', '/reconcile', array(
        'methods' => WP_REST_Server::CREATABLE,
        'permission_callback' => $permission,
        'args' => array(
            'post_id' => array( 'type' => 'integer', 'default' => 0, 'minimum' => 0 ),
            'force' => array( 'type' => 'boolean', 'default' => false ),
        ),
        'callback' => static function ( WP_REST_Request $request ) {
            $post_id = absint( $request->get_param( 'post_id' ) );
            $force = rest_sanitize_boolean( $request->get_param( 'force' ) );
            if ( $force && ! $post_id ) {
                return new WP_Error( 'invalid_force', 'A post_id is required for forced regeneration.',
                    array( 'status' => 400 ) );
            }
            $result = wikiai_hfcm_watchdog_run( $post_id, $force );
            return is_wp_error( $result ) ? $result : rest_ensure_response( $result );
        },
    ) );
} );
