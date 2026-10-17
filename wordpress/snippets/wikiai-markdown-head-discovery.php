<?php
/**
 * WikiAI Markdown Discovery Head v1.1.0
 *
 * Outputs GitHub Markdown alternates for published expert pages and
 * five organizational pages. Business profiles already have discovery links
 * from the active WikiAI entity layer; avoid duplicate head links.
 * The LLM Markdown plugin remains responsible for own-domain .md alternates.
 * The public GitHub mirror remains a secondary representation, never canonical.
 */

if ( ! defined( 'ABSPATH' ) ) {
    return;
}

add_action( 'wp_head', static function () {
    if ( ! is_singular() ) {
        return;
    }

    $post = get_queried_object();
    if ( ! ( $post instanceof WP_Post ) || 'publish' !== get_post_status( $post ) ) {
        return;
    }

    $markdown_path = '';

    if ( 'page' === $post->post_type ) {
        $core_pages = array(
            101 => 'wikiai/services.md',
            202 => 'wikiai/pricing.md',
             21 => 'wikiai/about.md',
             22 => 'wikiai/team.md',
             23 => 'wikiai/contact.md',
        );

        if ( isset( $core_pages[ (int) $post->ID ] ) ) {
            $markdown_path = $core_pages[ (int) $post->ID ];
        } else {
            $permalink = get_permalink( $post );
            $path      = $permalink ? wp_parse_url( $permalink, PHP_URL_PATH ) : '';

            // Experts/partners are discovered from their actual published URL.
            if ( is_string( $path ) && preg_match( '~^/szakertok/([a-z0-9-]+)/?$~', $path, $matches ) ) {
                if ( $post->post_name === $matches[1] ) {
                    $markdown_path = 'wikiai/people/' . $matches[1] . '.md';
                }
            }
        }
    } elseif ( 'post' === $post->post_type && 637 === (int) $post->ID ) {
        // The WikiAI.hu first-party profile is the one business exception.
        // Other companies already emit an alternate through the entity layer.
        $markdown_path = 'entities/wikiai-hu.md';
    }

    if ( '' === $markdown_path ) {
        return;
    }

    $github_url = 'https://raw.githubusercontent.com/WikiAI-hu/wikiai-entities/main/' . $markdown_path;

    printf(
        '<link rel="alternate" type="text/markdown" href="%s" title="WikiAI GitHub Markdown mirror" data-wikiai-markdown="github">' . "\n",
        esc_url( $github_url )
    );
}, 9 );
