<?php
/**
 * WikiAI HFCM read-only adapter 1.1.0.
 *
 * Supplies only the two authenticated legacy REST GET endpoints that the
 * existing Entity HTML Generator (#107) already consumes.
 *
 * No POST, PATCH, DELETE, HFCM mutation or publicly readable snippet source.
 * Access requires manage_options. The deprecated TEMP bridge stays disabled.
 */

if ( ! defined( 'ABSPATH' ) ) {
    return;
}

add_action( 'rest_api_init', static function () {
    $can_read = static function () {
        return current_user_can( 'manage_options' );
    };

    register_rest_route( 'wikiai-hfcm/v1', '/list', array(
        'methods'             => WP_REST_Server::READABLE,
        'permission_callback' => $can_read,
        'callback'            => static function () {
            global $wpdb;
            $table = $wpdb->prefix . 'hfcm_scripts';
            $rows = $wpdb->get_results(
                "SELECT script_id, name, location, display_on, s_posts, status,
                        LENGTH(snippet) AS snippet_len
                   FROM {$table}
                  ORDER BY script_id ASC",
                ARRAY_A
            );
            if ( null === $rows || '' !== $wpdb->last_error ) {
                return new WP_Error( 'wikiai_hfcm_read_error',
                    'Unable to read HFCM metadata.',
                    array( 'status' => 500 ) );
            }
            return rest_ensure_response( $rows );
        },
    ) );

    register_rest_route( 'wikiai-hfcm/v1', '/snippet-chunk/(?P<id>[0-9]+)', array(
        'methods'             => WP_REST_Server::READABLE,
        'permission_callback' => $can_read,
        'args'                => array(
            'id' => array( 'type' => 'integer', 'minimum' => 1, 'required' => true ),
            'offset' => array( 'type' => 'integer', 'minimum' => 0, 'default' => 0 ),
            'length' => array( 'type' => 'integer', 'minimum' => 1, 'maximum' => 2500, 'default' => 2200 ),
        ),
        'callback'            => static function ( WP_REST_Request $request ) {
            global $wpdb;
            $id     = absint( $request['id'] );
            $offset = max( 0, absint( $request->get_param( 'offset' ) ) );
            $length = min( 2500, max( 1, absint( $request->get_param( 'length' ) ?: 2200 ) ) );
            $table  = $wpdb->prefix . 'hfcm_scripts';
            $source = $wpdb->get_var(
                $wpdb->prepare( "SELECT snippet FROM {$table} WHERE script_id=%d", $id )
            );
            if ( null === $source ) {
                return new WP_Error( 'wikiai_hfcm_missing',
                    'The requested HFCM script does not exist.', array( 'status' => 404 ) );
            }

            // HFCM stores these scripts HTML-escaped on this site. The existing
            // Entity Generator expects literal <script> tags. Decode the *whole*
            // snippet BEFORE slicing so HTML entities never split across chunks.
            // Leave already decoded source untouched.
            if (
                false === stripos( $source, '<script' ) &&
                false !== stripos( $source, '&lt;script' )
            ) {
                $source = html_entity_decode( $source, ENT_QUOTES | ENT_HTML5, 'UTF-8' );
            }

            if ( function_exists( 'mb_substr' ) ) {
                $total = mb_strlen( $source, 'UTF-8' );
                $chunk = mb_substr( $source, $offset, $length, 'UTF-8' );
                $read  = mb_strlen( $chunk, 'UTF-8' );
            } else {
                $total = strlen( $source );
                $chunk = substr( $source, $offset, $length );
                $read  = strlen( $chunk );
            }
            return rest_ensure_response( array(
                'script_id' => $id,
                'offset'    => $offset,
                'length'    => $read,
                'total'     => $total,
                'chunk'     => $chunk,
            ) );
        },
    ) );
} );
