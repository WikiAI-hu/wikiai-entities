<?php
/**
 * WikiAI Entity Discovery Layer v0.2.2
 * Stable pure-PHP implementation.
 */

if ( ! defined( 'ABSPATH' ) ) { return; }

if ( ! function_exists( 'wikiai_ed2_atomic_write' ) ) {

function wikiai_ed2_atomic_write( $path, $content ) {
    $tmp = $path . '.tmp-' . wp_generate_password( 8, false, false );
    $bytes = file_put_contents( $tmp, $content, LOCK_EX );
    if ( false === $bytes ) {
        @unlink( $tmp );
        return false;
    }
    @chmod( $tmp, 0644 );
    if ( ! @rename( $tmp, $path ) ) {
        @unlink( $tmp );
        return false;
    }
    @chmod( $path, 0644 );
    return (int) $bytes;
}

function wikiai_ed2_patch_entity_file( $path ) {
    if ( ! is_file( $path ) || ! is_readable( $path ) ) { return false; }

    $html = file_get_contents( $path );
    if ( false === $html ) { return false; }

    $robots = '<meta name="robots" content="index,follow">';
    $google = '<meta name="googlebot" content="noindex,follow">';

    if ( preg_match( '#<meta\s+name=["\']robots["\'][^>]*>#i', $html ) ) {
        $html = preg_replace( '#<meta\s+name=["\']robots["\'][^>]*>#i', $robots, $html, 1 );
    } elseif ( false !== stripos( $html, '</head>' ) ) {
        $html = preg_replace( '#</head>#i', $robots . "\n</head>", $html, 1 );
    }

    if ( preg_match( '#<meta\s+name=["\']googlebot["\'][^>]*>#i', $html ) ) {
        $html = preg_replace( '#<meta\s+name=["\']googlebot["\'][^>]*>#i', $google, $html, 1 );
    } elseif ( preg_match( '#<meta\s+name=["\']robots["\'][^>]*>#i', $html, $m, PREG_OFFSET_CAPTURE ) ) {
        $tag = $m[0][0];
        $pos = $m[0][1] + strlen( $tag );
        $html = substr( $html, 0, $pos ) . "\n" . $google . substr( $html, $pos );
    } elseif ( false !== stripos( $html, '</head>' ) ) {
        $html = preg_replace( '#</head>#i', $google . "\n</head>", $html, 1 );
    }

    return wikiai_ed2_atomic_write( $path, $html );
}

function wikiai_ed2_business_ids() {
    return get_posts( array(
        'post_type'      => 'post',
        'post_status'    => 'publish',
        'category'       => 8,
        'posts_per_page' => -1,
        'orderby'        => 'title',
        'order'          => 'ASC',
        'exclude'        => array( 637 ),
        'fields'         => 'ids',
    ) );
}

function wikiai_ed2_build_index() {
    $dir = trailingslashit( ABSPATH ) . 'entity';
    if ( ! is_dir( $dir ) && ! wp_mkdir_p( $dir ) ) { return false; }
    @chmod( $dir, 0755 );

    $items = '';

    foreach ( wikiai_ed2_business_ids() as $post_id ) {
        $slug = get_post_field( 'post_name', $post_id );
        if ( ! $slug ) { continue; }

        $file = $dir . '/' . $slug . '.html';
        if ( ! is_file( $file ) ) { continue; }

        $name = wp_strip_all_tags( get_the_title( $post_id ) );
        $machine = home_url( '/entity/' . $slug . '.html' );
        $human = get_permalink( $post_id );
        $md = 'https://raw.githubusercontent.com/WikiAI-hu/wikiai-entities/main/entities/' . rawurlencode( $slug ) . '.md';
        $jsonld = 'https://raw.githubusercontent.com/WikiAI-hu/wikiai-entities/main/entities/' . rawurlencode( $slug ) . '.jsonld';

        $items .= '<li><strong>' . esc_html( $name ) . '</strong> — ';
        $items .= '<a href="' . esc_url( $machine ) . '">Machine HTML</a> — ';
        $items .= '<a href="' . esc_url( $human ) . '">Canonical human profile</a> — ';
        $items .= '<a href="' . esc_url( $md ) . '">Markdown</a> — ';
        $items .= '<a href="' . esc_url( $jsonld ) . '">JSON-LD</a></li>' . "\n";
    }

    $generated = current_time( DATE_W3C );

    $html = '<!doctype html>' . "\n";
    $html .= '<html lang="hu-HU"><head>' . "\n";
    $html .= '<meta charset="utf-8">' . "\n";
    $html .= '<meta name="viewport" content="width=device-width,initial-scale=1">' . "\n";
    $html .= '<title>WikiAI Machine Entity Directory</title>' . "\n";
    $html .= '<meta name="description" content="A WikiAI.hu publikált vállalkozási gépi entitásrekordjainak crawlolható indexe.">' . "\n";
    $html .= '<meta name="robots" content="index,follow">' . "\n";
    $html .= '<meta name="googlebot" content="noindex,follow">' . "\n";
    $html .= '<link rel="canonical" href="' . esc_url( home_url( '/entity/' ) ) . '">' . "\n";
    $html .= '<link rel="alternate" type="text/plain" href="' . esc_url( home_url( '/llms.txt' ) ) . '" title="WikiAI llms.txt">' . "\n";
    $html .= '<link rel="alternate" type="application/json" href="https://raw.githubusercontent.com/WikiAI-hu/wikiai-entities/main/manifest.json" title="WikiAI GitHub entity manifest">' . "\n";
    $html .= '<meta name="generator" content="WikiAI Entity Discovery Layer 0.2.2">' . "\n";
    $html .= '</head><body data-record-type="wikiai-machine-entity-directory" data-language="hu-HU">' . "\n";
    $html .= '<main><header><h1>WikiAI Machine Entity Directory</h1>' . "\n";
    $html .= '<p>Publikus, gépi feldolgozásra készült vállalkozási entitásrekordok. A humán profilok a WikiAI.hu megfelelő vállalkozásoldalai.</p>' . "\n";
    $html .= '<p>Generálva: <time datetime="' . esc_attr( $generated ) . '">' . esc_html( $generated ) . '</time></p></header>' . "\n";
    $html .= '<nav aria-label="Machine entity records"><ul>' . "\n" . $items . '</ul></nav>' . "\n";
    $html .= '<section><h2>Discovery resources</h2><ul>' . "\n";
    $html .= '<li><a href="' . esc_url( home_url( '/llms.txt' ) ) . '">WikiAI llms.txt</a></li>' . "\n";
    $html .= '<li><a href="https://raw.githubusercontent.com/WikiAI-hu/wikiai-entities/main/entities.md">GitHub entity index</a></li>' . "\n";
    $html .= '<li><a href="https://raw.githubusercontent.com/WikiAI-hu/wikiai-entities/main/manifest.json">GitHub entity manifest</a></li>' . "\n";
    $html .= '<li><a href="' . esc_url( home_url( '/robots.txt' ) ) . '">robots.txt</a></li>' . "\n";
    $html .= '</ul></section></main></body></html>' . "\n";

    return wikiai_ed2_atomic_write( $dir . '/index.html', $html );
}

function wikiai_ed2_update_llms() {
    $path = trailingslashit( ABSPATH ) . 'llms.txt';
    if ( ! is_file( $path ) || ! is_readable( $path ) ) { return false; }

    $content = file_get_contents( $path );
    if ( false === $content ) { return false; }

    if ( false !== strpos( $content, 'WikiAI Machine Entity HTML index' ) ) {
        return 0;
    }

    $line = '- [WikiAI Machine Entity HTML index](' . home_url( '/entity/' ) . '): crawlolható szemantikus HTML entitáskönyvtár; Googlebot számára noindex, más gépi kliensek számára nyilvánosan elérhető.';

    $heading = '## Primary machine-readable indexes';
    if ( false !== strpos( $content, $heading ) ) {
        $content = str_replace( $heading, $heading . "\n" . $line, $content );
    } else {
        $content .= "\n\n## Machine entity HTML\n" . $line . "\n";
    }

    return wikiai_ed2_atomic_write( $path, $content );
}

function wikiai_ed2_sync_all() {
    $dir = trailingslashit( ABSPATH ) . 'entity';
    $patched = 0;

    if ( is_dir( $dir ) ) {
        @chmod( $dir, 0755 );

        foreach ( glob( $dir . '/*.html' ) ?: array() as $file ) {
            if ( 'index.html' === basename( $file ) ) { continue; }
            if ( false !== wikiai_ed2_patch_entity_file( $file ) ) {
                $patched++;
            }
        }
    }

    $index = wikiai_ed2_build_index();
    $llms = wikiai_ed2_update_llms();

    update_option( 'wikiai_ed2_last_sync', array(
        'time'    => current_time( 'mysql', true ),
        'patched' => $patched,
        'index'   => $index,
        'llms'    => $llms,
    ), false );

    return array(
        'patched' => $patched,
        'index'   => $index,
        'llms'    => $llms,
    );
}

add_action( 'init', function() {
    $version = (string) get_option( 'wikiai_ed2_version', '' );

    if ( '0.2.2' !== $version ) {
        $result = wikiai_ed2_sync_all();
        if ( is_array( $result ) ) {
            update_option( 'wikiai_ed2_version', '0.2.2', false );
        }
    }
}, 20 );

add_action( 'save_post_post', function( $post_id ) {
    if ( wp_is_post_revision( $post_id ) || wp_is_post_autosave( $post_id ) ) { return; }
    if ( 637 === (int) $post_id || ! has_category( 8, $post_id ) || 'publish' !== get_post_status( $post_id ) ) { return; }

    $relative = (string) get_post_meta( $post_id, '_wikiai_entity_html_path', true );
    if ( $relative ) {
        $path = trailingslashit( ABSPATH ) . ltrim( $relative, '/' );
        if ( is_file( $path ) ) {
            wikiai_ed2_patch_entity_file( $path );
        }
    }

    wikiai_ed2_build_index();
}, 200, 1 );

add_action( 'wp_head', function() {
    if ( ! is_single() ) { return; }

    $post_id = get_queried_object_id();
    if ( ! $post_id || 637 === (int) $post_id || ! has_category( 8, $post_id ) || 'publish' !== get_post_status( $post_id ) ) { return; }

    $slug = get_post_field( 'post_name', $post_id );
    if ( ! $slug ) { return; }

    echo "\n" . '<link rel="alternate" type="text/html" href="' . esc_url( home_url( '/entity/' . $slug . '.html' ) ) . '" title="WikiAI Machine Entity Record">' . "\n";
    echo '<link rel="alternate" type="text/markdown" href="' . esc_url( 'https://raw.githubusercontent.com/WikiAI-hu/wikiai-entities/main/entities/' . rawurlencode( $slug ) . '.md' ) . '" title="WikiAI Markdown Entity Mirror">' . "\n";
    echo '<link rel="alternate" type="application/ld+json" href="' . esc_url( 'https://raw.githubusercontent.com/WikiAI-hu/wikiai-entities/main/entities/' . rawurlencode( $slug ) . '.jsonld' ) . '" title="WikiAI JSON-LD Entity Mirror">' . "\n";
}, 30 );

add_action( 'rest_api_init', function() {
    register_rest_route( 'wikiai-entity/v2', '/discovery-status', array(
        'methods' => WP_REST_Server::READABLE,
        'permission_callback' => function() {
            return current_user_can( 'edit_posts' );
        },
        'callback' => function() {
            $dir = trailingslashit( ABSPATH ) . 'entity';
            $files = array();

            foreach ( glob( $dir . '/*.html' ) ?: array() as $file ) {
                $html = is_readable( $file ) ? file_get_contents( $file ) : '';
                $files[ basename( $file ) ] = array(
                    'bytes' => is_file( $file ) ? filesize( $file ) : 0,
                    'googlebot_noindex' => is_string( $html ) && false !== stripos( $html, '<meta name="googlebot" content="noindex,follow">' ),
                );
            }

            return rest_ensure_response( array(
                'version' => get_option( 'wikiai_ed2_version', '' ),
                'last_sync' => get_option( 'wikiai_ed2_last_sync', array() ),
                'directory' => home_url( '/entity/' ),
                'files' => $files,
                // The site uses a virtual llms.txt from Code Snippets #102.
                // The previous status falsely checked only a physical file.
                'llms_has_entity_index' => function_exists( 'wikiai_llms_build_document' )
                    ? false !== strpos( (string) wikiai_llms_build_document(), 'WikiAI Machine Entity HTML index' )
                    : (
                        is_readable( trailingslashit( ABSPATH ) . 'llms.txt' ) &&
                        false !== strpos(
                            (string) file_get_contents( trailingslashit( ABSPATH ) . 'llms.txt' ),
                            'WikiAI Machine Entity HTML index'
                        )
                    ),
                'llms_source' => function_exists( 'wikiai_llms_build_document' )
                    ? 'virtual-code-snippets' : 'physical-or-unavailable',
            ) );
        },
    ) );
} );

}
