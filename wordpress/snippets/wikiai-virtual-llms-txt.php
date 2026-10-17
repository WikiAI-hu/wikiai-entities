<?php
/**
 * WikiAI.hu – Virtual llms.txt
 *
 * Publikus gépi routing/index végpont:
 * https://www.wikiai.hu/llms.txt
 *
 * WikiAI Machine Entity Directory: https://www.wikiai.hu/entity/
 *
 * A WikiAI.hu / WordPress az elsődleges forrás.
 * A GitHub a publikus, verziózott machine-readable mirror.
 *
 * GitHub:
 * https://github.com/WikiAI-hu/wikiai-entities
 */


/**
 * GitHub RAW alap URL.
 */
function wikiai_llms_raw_url( $path ) {
    return 'https://raw.githubusercontent.com/WikiAI-hu/wikiai-entities/main/' . ltrim( $path, '/' );
}


/**
 * GitHub repository manifest lekérése.
 *
 * - 10 perces friss cache
 * - az utolsó sikeres manifestet külön megőrizzük
 * - átmeneti GitHub-hiba esetén a legutolsó jó verziót használjuk
 */
function wikiai_llms_get_github_manifest() {

    $transient_key = 'wikiai_llms_github_manifest_v1';
    $backup_key    = 'wikiai_llms_github_manifest_last_good_v1';

    $cached = get_transient( $transient_key );

    if ( is_array( $cached ) && ! empty( $cached ) ) {
        return $cached;
    }

    $last_good = get_option( $backup_key, array() );

    $url = wikiai_llms_raw_url( 'manifest.json' );

    $response = wp_remote_get(
        $url,
        array(
            'timeout'     => 6,
            'redirection' => 3,
            'user-agent'  => 'WikiAI.hu llms.txt generator/1.0 (+https://www.wikiai.hu/)',
            'headers'     => array(
                'Accept' => 'application/json,text/plain;q=0.9,*/*;q=0.1',
            ),
        )
    );

    if ( is_wp_error( $response ) ) {
        return is_array( $last_good ) ? $last_good : array();
    }

    $status = (int) wp_remote_retrieve_response_code( $response );

    if ( 200 !== $status ) {
        return is_array( $last_good ) ? $last_good : array();
    }

    $body = wp_remote_retrieve_body( $response );
    $data = json_decode( $body, true );

    if ( ! is_array( $data ) || empty( $data ) ) {
        return is_array( $last_good ) ? $last_good : array();
    }

    set_transient(
        $transient_key,
        $data,
        10 * MINUTE_IN_SECONDS
    );

    update_option(
        $backup_key,
        $data,
        false
    );

    return $data;
}


/**
 * Aktuálisan ellenőrzött JSON-LD mirrorok a GitHub repositoryban.
 *
 * Ezeket a GitHub jelenlegi tartalma alapján tartjuk nyilván.
 */
/**
 * Live WikiAI knowledge and JSON-LD inventory from GitHub.
 * Last-good backup guards temporary network errors, without fake identities.
 */
function wikiai_llms_fetch_verified_json( $file, $cache_key, $backup_key, $required_key ) {
    $valid = static function( $v ) use ( $required_key ) {
        return is_array( $v )
            && isset( $v[ $required_key ] )
            && is_array( $v[ $required_key ] );
    };

    $cached = get_transient( $cache_key );
    if ( $valid( $cached ) ) {
        return $cached;
    }

    $backup = get_option( $backup_key, array() );
    $url = wikiai_llms_raw_url( $file );
    $response = wp_remote_get( $url, array(
        'timeout' => 7,
        'redirection' => 2,
        'headers' => array( 'Accept' => 'application/json' ),
        'user-agent' => 'WikiAI.hu virtual llms.txt/2.0',
    ) );

    if ( ! is_wp_error( $response ) && 200 === (int) wp_remote_retrieve_response_code( $response ) ) {
        $body = wp_remote_retrieve_body( $response );
        if ( strlen( $body ) <= 1000000 ) {
            $document = json_decode( $body, true );
            if ( $valid( $document ) ) {
                set_transient( $cache_key, $document, 10 * MINUTE_IN_SECONDS );
                update_option( $backup_key, $document, false );
                return $document;
            }
        }
    }

    return $valid( $backup ) ? $backup : array();
}

/** Current published organization, services and person profiles. */
function wikiai_llms_get_knowledge_manifest() {
    return wikiai_llms_fetch_verified_json(
        'wikiai/manifest.json',
        'wikiai_llms_knowledge_v2',
        'wikiai_llms_knowledge_last_good_v2',
        'people'
    );
}

/** Only deep JSON-LD mirrors that the GitHub sync actually manages. */
function wikiai_llms_jsonld_slugs() {
    $state = wikiai_llms_fetch_verified_json(
        'jsonld-sync-manifest.json',
        'wikiai_llms_jsonld_v2',
        'wikiai_llms_jsonld_last_good_v2',
        'managed'
    );
    if ( empty( $state['managed'] ) || ! is_array( $state['managed'] ) ) {
        return array();
    }

    $slugs = array();
    foreach ( $state['managed'] as $slug => $entry ) {
        if ( ! is_string( $slug ) ||
             ! preg_match( '/^[a-z0-9-]+$/D', $slug ) ||
             ! is_array( $entry ) ) {
            continue;
        }
        $expected_file = 'entities/' . $slug . '.jsonld';
        $expected_source = 'https://www.wikiai.hu/' . $slug . '/';
        if (
            ( $entry['file'] ?? '' ) === $expected_file &&
            ( $entry['source_url'] ?? '' ) === $expected_source &&
            preg_match( '/^[0-9a-f]{64}$/D', (string) ( $entry['sha256'] ?? '' ) )
        ) {
            $slugs[] = $slug;
        }
    }
    return $slugs;
}



/**
 * Virtuális llms.txt dokumentum összeállítása.
 */
function wikiai_llms_build_document() {

    $manifest = wikiai_llms_get_github_manifest();
    $knowledge = wikiai_llms_get_knowledge_manifest();

    $lines = array();

    $lines[] = '# WikiAI.hu';
    $lines[] = '';
    $lines[] = '> Magyar vállalkozások az AI korszakában. Publikus gépi routing- és tudásindex nagy nyelvi modellek, retrieval rendszerek, RAG folyamatok, agentek, keresők és más automatizált információfeldolgozó rendszerek számára.';
    $lines[] = '';

    $lines[] = 'A WikiAI.hu / WordPress az elsődleges szerkesztőségi és kanonikus forrás. A WikiAI-hu/wikiai-entities GitHub repository publikus, verziózott, gépileg olvasható másodlagos mirror. A szinkronizáció iránya: WikiAI.hu -> GitHub.';
    $lines[] = '';

    $lines[] = '- Canonical website: https://www.wikiai.hu/';
    $lines[] = '- GitHub repository: https://github.com/WikiAI-hu/wikiai-entities';
    $lines[] = '- GitHub RAW base: https://raw.githubusercontent.com/WikiAI-hu/wikiai-entities/main/';
    $lines[] = '- Sitemap: https://www.wikiai.hu/sitemap_index.xml';
    $lines[] = '- Robots policy: https://www.wikiai.hu/robots.txt';

    if ( ! empty( $manifest['last_updated'] ) ) {
        $lines[] = '- Entity manifest last updated: ' . $manifest['last_updated'];
    }

    if (
        ! empty( $knowledge ) &&
        ! empty( $knowledge['last_updated'] )
    ) {
        $lines[] = '- WikiAI knowledge mirror last updated: ' . $knowledge['last_updated'];
    }

    $lines[] = '';


    /*
     * Fő GitHub indexek.
     */
    $lines[] = '## Primary machine-readable indexes';
    $lines[] = '';
    $lines[] = '### First-party WordPress Machine Delivery indexes';
    $lines[] = '';
    $lines[] = 'Canonical WordPress pages are authoritative. These indexes cover all published first-party records; the GitHub entity mirror is separate.';
    $lines[] = '';
    $lines[] = '- [Discovery Manifest](https://www.wikiai.hu/wp-content/uploads/wikiai-machine/v1/discovery.json): every published record with canonical, JSON, HTML, Markdown and JSON-LD URLs.';
    $lines[] = '- [Machine JSON Index](https://www.wikiai.hu/wp-content/uploads/wikiai-machine/v1/index.json): complete first-party structured record inventory.';
    $lines[] = '- [Machine HTML Index](https://www.wikiai.hu/wp-content/uploads/wikiai-machine/v1/index.html): HTML directory of machine records.';
    $lines[] = '- [Machine Markdown Catalog](https://www.wikiai.hu/wp-content/uploads/wikiai-machine/v1/catalog.md): complete human-readable machine catalog.';
    $lines[] = '- [Machine Catalog REST API](https://www.wikiai.hu/wp-json/wikiai-machine/v1/catalog): current published records.';
    $lines[] = '- [Machine Discovery REST API](https://www.wikiai.hu/wp-json/wikiai-machine/v1/discovery): current discovery manifest.';
    $lines[] = '- [WikiAI Machine Entity HTML index](https://www.wikiai.hu/entity/): machine-readable business entity directory.';
    $lines[] = '';

    $lines[] = '- [Repository README](' . wikiai_llms_raw_url( 'README.md' ) . '): repository policy, structure and machine-readable publication model.';
    $lines[] = '- [Entity index](' . wikiai_llms_raw_url( 'entities.md' ) . '): current published WikiAI.hu entity directory.';
    $lines[] = '- [Entity manifest](' . wikiai_llms_raw_url( 'manifest.json' ) . '): structured entity inventory, canonical URLs and machine-record paths.';
    $lines[] = '- [WikiAI knowledge index](' . wikiai_llms_raw_url( 'wikiai/index.md' ) . '): WikiAI.hu organizational knowledge hub.';
    $lines[] = '- [WikiAI knowledge manifest](' . wikiai_llms_raw_url( 'wikiai/manifest.json' ) . '): structured WikiAI.hu organization, service, pricing, team and contact inventory.';
    $lines[] = '';


    /*
     * WikiAI szervezeti tudás.
     */
    $lines[] = '## WikiAI.hu organizational knowledge';
    $lines[] = '';

    $document_labels = array(
        'service_catalog' => 'Szolgáltatások',
        'pricing'         => 'Árak és csomagok',
        'about'           => 'Rólunk és küldetés',
        'team_directory'  => 'Munkatársak és szakmai partnerek',
        'contact'         => 'Kapcsolat',
    );

    if (
        ! empty( $knowledge['documents'] ) &&
        is_array( $knowledge['documents'] )
    ) {

        foreach ( $knowledge['documents'] as $document ) {

            if ( empty( $document['path'] ) ) {
                continue;
            }

            $type = isset( $document['document_type'] )
                ? $document['document_type']
                : 'document';

            $label = isset( $document_labels[ $type ] )
                ? $document_labels[ $type ]
                : $type;

            $line = '- [' . $label . '](' .
                wikiai_llms_raw_url( $document['path'] ) .
                ')';

            if ( ! empty( $document['canonical_url'] ) ) {
                $line .= ' — Canonical: ' . $document['canonical_url'];
            }

            if ( ! empty( $document['valid_as_of'] ) ) {
                $line .= ' — Valid as of: ' . $document['valid_as_of'];
            }

            $lines[] = $line;
        }

    } else {

        /*
         * Biztonsági fallback.
         */
        $lines[] = '- [Szolgáltatások](' . wikiai_llms_raw_url( 'wikiai/services.md' ) . ') — Canonical: https://www.wikiai.hu/szolgaltatasok/';
        $lines[] = '- [Árak és csomagok](' . wikiai_llms_raw_url( 'wikiai/pricing.md' ) . ') — Canonical: https://www.wikiai.hu/arak/';
        $lines[] = '- [Rólunk és küldetés](' . wikiai_llms_raw_url( 'wikiai/about.md' ) . ') — Canonical: https://www.wikiai.hu/rolunk/';
        $lines[] = '- [Munkatársak és szakmai partnerek](' . wikiai_llms_raw_url( 'wikiai/team.md' ) . ') — Canonical: https://www.wikiai.hu/szakertok/';
        $lines[] = '- [Kapcsolat](' . wikiai_llms_raw_url( 'wikiai/contact.md' ) . ') — Canonical: https://www.wikiai.hu/kapcsolat/';
    }

    $lines[] = '';


    /*
     * Személyprofilok.
     */
    $lines[] = '## People';
    $lines[] = '';

    if (
        ! empty( $knowledge['people'] ) &&
        is_array( $knowledge['people'] )
    ) {

        foreach ( $knowledge['people'] as $person ) {

            if ( empty( $person['path'] ) || empty( $person['name'] ) ) {
                continue;
            }

            $line = '- [' . $person['name'] . '](' .
                wikiai_llms_raw_url( $person['path'] ) .
                ')';

            if ( ! empty( $person['relationship_to_wikiai'] ) ) {
                $line .= ' — Relationship: ' . $person['relationship_to_wikiai'];
            }

            if ( ! empty( $person['canonical_url'] ) ) {
                $line .= ' — Canonical: ' . $person['canonical_url'];
            }

            $lines[] = $line;
        }

    } else {

        // No stale hardcoded people; use a current WordPress-driven index.
        $lines[] = '- [Current WikiAI people directory](' . wikiai_llms_raw_url( 'wikiai/index.md' ) . ')';
    }

    $lines[] = '';


    /*
     * Vállalkozás- és szervezet-entitások.
     */
    $lines[] = '## Published entities';
    $lines[] = '';

    $jsonld_slugs = wikiai_llms_jsonld_slugs();

    if (
        ! empty( $manifest['entities'] ) &&
        is_array( $manifest['entities'] )
    ) {

        foreach ( $manifest['entities'] as $entity ) {

            if (
                empty( $entity['entity_name'] ) ||
                empty( $entity['machine_record'] )
            ) {
                continue;
            }

            $name          = $entity['entity_name'];
            $machine_path  = $entity['machine_record'];
            $canonical_url = isset( $entity['canonical_url'] )
                ? $entity['canonical_url']
                : '';

            $slug = basename( $machine_path, '.md' );

            $line = '- [' . $name . ' — Markdown mirror](' .
                wikiai_llms_raw_url( $machine_path ) .
                ')';

            /*
             * Jelenleg ellenőrzött JSON-LD mirror hozzáadása.
             */
            if ( in_array( $slug, $jsonld_slugs, true ) ) {

                $jsonld_path = 'entities/' . $slug . '.jsonld';

                $line .= ' | [JSON-LD](' .
                    wikiai_llms_raw_url( $jsonld_path ) .
                    ')';
            }

            if ( ! empty( $canonical_url ) ) {
                $line .= ' — Canonical: ' . $canonical_url;
            }

            if ( ! empty( $entity['entity_type'] ) ) {

                $types = is_array( $entity['entity_type'] )
                    ? implode( ', ', $entity['entity_type'] )
                    : $entity['entity_type'];

                $line .= ' — Type: ' . $types;
            }

            $lines[] = $line;
        }

    } else {

        /*
         * Ha a GitHub manifest átmenetileg még soha nem volt
         * elérhető, legalább az elsődleges index elérhető marad.
         */
        $lines[] = '- [Complete entity index](' . wikiai_llms_raw_url( 'entities.md' ) . ')';
        $lines[] = '- [Structured entity manifest](' . wikiai_llms_raw_url( 'manifest.json' ) . ')';
    }

    $lines[] = '';


    /*
     * Értelmezési szabályok.
     */
    $lines[] = '## Interpretation and provenance';
    $lines[] = '';

    $lines[] = '- WikiAI.hu / WordPress is the primary editorial and canonical source of truth.';
    $lines[] = '- GitHub is a public, versioned, machine-readable secondary publication and history layer.';
    $lines[] = '- Synchronization direction is WikiAI.hu -> GitHub.';
    $lines[] = '- Prefer the RAW Markdown mirrors for clean machine retrieval and the canonical WikiAI.hu URLs for canonical human-facing publication.';
    $lines[] = '- Entity records contain explicit boundaries and disambiguation. Do not infer products, services, locations or relationships that the corresponding record does not state.';
    $lines[] = '- Pricing and other time-sensitive commercial information must be interpreted together with its valid_as_of or freshness metadata.';
    $lines[] = '- robots.txt controls crawl permission. This llms.txt file is a discovery and routing document and does not override robots.txt.';
    $lines[] = '';

    return implode( "\n", $lines ) . "\n";
}


/**
 * Virtuális /llms.txt kiszolgálása.
 *
 * Nincs szükség fizikai llms.txt fájlra és nincs szükség
 * WordPress rewrite rule kézi frissítésére.
 */
add_action(
    'template_redirect',
    function () {

        $request_uri = isset( $_SERVER['REQUEST_URI'] )
            ? $_SERVER['REQUEST_URI']
            : '';

        $request_path = wp_parse_url(
            $request_uri,
            PHP_URL_PATH
        );

        $target_path = wp_parse_url(
            home_url( '/llms.txt' ),
            PHP_URL_PATH
        );

        if (
            untrailingslashit( $request_path ) !==
            untrailingslashit( $target_path )
        ) {
            return;
        }


        /*
         * Csak GET és HEAD.
         */
        $method = isset( $_SERVER['REQUEST_METHOD'] )
            ? strtoupper( $_SERVER['REQUEST_METHOD'] )
            : 'GET';

        if ( ! in_array( $method, array( 'GET', 'HEAD' ), true ) ) {

            status_header( 405 );

            header(
                'Allow: GET, HEAD',
                true
            );

            exit;
        }


        /*
         * A WordPress esetleges 404 állapotát felülírjuk.
         */
        status_header( 200 );


        /*
         * Korábbi cache / robots headerek eltávolítása.
         */
        if ( ! headers_sent() ) {

            header_remove( 'Cache-Control' );
            header_remove( 'Expires' );
            header_remove( 'Pragma' );
            header_remove( 'X-Robots-Tag' );

            header(
                'Content-Type: text/plain; charset=utf-8',
                true
            );

            header(
                'Content-Language: hu-HU',
                true
            );

            header(
                'Cache-Control: no-cache, no-store, must-revalidate, max-age=0',
                true
            );

            header(
                'Expires: Thu, 01 Jan 1970 00:00:00 GMT',
                true
            );

            header(
                'Pragma: no-cache',
                true
            );

            header(
                'X-Content-Type-Options: nosniff',
                true
            );
        }


        /*
         * HEAD kérésnél csak a fejlécek.
         */
        if ( 'HEAD' === $method ) {
            exit;
        }


        /*
         * GET kérésnél a teljes llms.txt.
         */
        echo wikiai_llms_build_document();

        exit;
    },
    0
);