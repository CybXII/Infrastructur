# Registry-, Provenance- und Image-Security-Strategie

## Zweck

Dieses Dokument definiert die verbindliche Container-Registry- und Image-Security-Strategie der Merchfactory Container Platform ab v0.5. Es setzt Issue #74 um und ergänzt die Compose-, Security- und CI/CD-Standards.

Ziele:

- eindeutig vertrauenswürdige Image-Quellen,
- unveränderliche Deployments,
- nachvollziehbare Herkunft eigener Images,
- automatisierte Schwachstellenprüfung,
- kontrollierte Aufbewahrung und Bereinigung.

## Eigene Images

Eigene Merchfactory-Images werden in GitHub Container Registry unter folgendem Namespace veröffentlicht:

```text
ghcr.io/merchfactory/<image>
```

Standardmäßig bleiben eigene produktive Images privat. GitHub Actions verwendet nach Möglichkeit den repositorygebundenen `GITHUB_TOKEN` statt langlebiger persönlicher Registry-Tokens.

Ein Image wird nur dann als First-Party akzeptiert, wenn der kanonische Repositoryname mit `ghcr.io/merchfactory/` beginnt.

## Drittanbieter-Images

Drittanbieter-Images sind Default-Deny.

Zulässig sind nur Repositories, die in `configuration/container-image-policy.json` explizit eingetragen sind. Aktuell:

- `docker.io/library/traefik` für den Reverse Proxy,
- `docker.io/traefik/whoami` ausschließlich für Integrationstests,
- `quay.io/prometheus/prometheus` für die zentrale Metrikplattform.

Neue Quellen benötigen einen PR mit:

1. fachlichem Zweck,
2. Upstream-/Maintainer-Prüfung,
3. Lizenz- und Betriebsbewertung,
4. Vulnerability-Scan,
5. dokumentierter Signatur-/Provenance-Situation.

Ein beliebiges Image aus einer grundsätzlich erlaubten Registry ist nicht automatisch vertrauenswürdig.

## Explizite Registry-Namen

Kurzformen wie:

```text
traefik@sha256:...
```

sind in Deployment-Manifesten nicht zulässig.

Verwendet wird der vollständige Registry-/Repositoryname:

```text
docker.io/library/traefik@sha256:...
```

Dadurch ist die tatsächliche Bezugsquelle reviewbar und nicht von impliziten Docker-Namensregeln abhängig.

## Digest-Pinning

Alle Deployment- und Testimages werden mit vollständigem SHA-256-Digest referenziert:

```text
<registry>/<repository>@sha256:<64 hex characters>
```

Tags dürfen zusätzlich als Release-Metadaten existieren, bestimmen aber nicht den produktiven Sollzustand.

`:latest`, bewegliche Major-/Minor-Tags und rein tagbasierte Deployments sind unzulässig.

## First-Party-Provenance

Für eigene Images ist eine kryptographisch signierte Build-Provenance verpflichtend.

Das v0.5-Zielmodell verwendet GitHub Artifact Attestations. Build-Workflows erzeugen die Attestation nach dem Push des Images. Vor Promotion bzw. Deployment wird sie gegen das erwartete Quellrepository verifiziert.

Beispiel der späteren Verifikation:

```bash
gh attestation verify \
  oci://ghcr.io/merchfactory/example-service@sha256:<digest> \
  --repo Merchfactory/<source-repository>
```

Die Attestation ersetzt nicht das Digest-Pinning; sie beantwortet zusätzlich die Frage, welcher vertrauenswürdige Build-Workflow das Artefakt erzeugt hat.

Eine separate Cosign-Image-Signatur kann später ergänzt werden. Für v0.5 ist die GitHub-/Sigstore-basierte Provenance-Attestation der verbindliche First-Party-Nachweis.

## Drittanbieter-Provenance

Bei Drittanbieter-Images wird eine vorhandene Upstream-Signatur oder Provenance nach Möglichkeit verifiziert.

Fehlt ein belastbarer Upstream-Nachweis, ist das Image nicht automatisch verboten. Die kompensierenden Kontrollen sind dann:

- exakte Repository-Allowlist,
- SHA-256-Digest,
- Vulnerability-Scan,
- bewusstes Versionsupdate per PR,
- Review des offiziellen Upstream-Projekts.

Diese Ausnahme vom First-Party-Provenance-Modell gilt nur für explizit genehmigte Drittanbieter-Repositories.

## Vulnerability-Scanning

Trivy ist das Standardwerkzeug für Container-Vulnerability-Scans.

Die CI installiert eine feste Trivy-Version über eine auf Commit-SHA gepinnte Setup-Action. Es wird nicht `latest` verwendet.

### Reporting

Alle HIGH- und CRITICAL-Funde werden sichtbar gemacht.

### Blocking Gate

Der Merge/Release wird blockiert, wenn Trivy eine CRITICAL-Schwachstelle mit verfügbarem Fix erkennt.

Ungefixte CRITICAL-Funde werden weiterhin berichtet, blockieren aber nicht automatisch. Sie benötigen eine dokumentierte Bewertung und können abhängig von Exponierung und Ausnutzbarkeit trotzdem einen Release-Stop auslösen.

### Ausnahmen

Eine Security-Ausnahme benötigt mindestens:

- Issue,
- Risikobewertung,
- Owner,
- Ablaufdatum.

Unbefristete Ignore-Einträge sind nicht zulässig.

## Scan-Zeitpunkte

### Eigene Images

Mindestens:

1. nach dem Build und vor Promotion,
2. vor Deployment eines neuen Digests,
3. erneut bei sicherheitsrelevanten Änderungen oder aktualisierter Vulnerability-Datenbank.

### Plattform-/Drittanbieter-Images

Die im Infrastructure-Repository eingesetzten Images werden in der Image-Security-CI erneut gescannt, wenn sich Compose-Dateien, die Registry-Policy oder der Security-Workflow ändern.

Zusätzlich bleiben regelmäßige Security-Reviews gemäß `docs/04-security.md` erforderlich, weil neue CVEs auch ohne Imageänderung bekannt werden können.

## Maschinenlesbare Policy

Quelle:

```text
configuration/container-image-policy.json
```

Validierung:

```bash
python3 scripts/validate-image-policy.py <compose-file> [<overlay> ...]
```

Die Prüfung erzwingt:

- vollständiges Digest-Pinning,
- expliziten Registry-Namen,
- First-Party-Namespace,
- exakte Drittanbieter-Allowlist.

## GHCR-Berechtigungsmodell

Für private eigene Images gilt Least Privilege.

- Build-Workflows erhalten `packages: write` nur für den Publish-Job.
- Scan-/Deployment-Workflows erhalten höchstens `packages: read`.
- Repositorygebundener `GITHUB_TOKEN` wird bevorzugt.
- PATs werden nur eingesetzt, wenn ein repositoryübergreifender Zugriff technisch nicht mit `GITHUB_TOKEN` abbildbar ist.
- Paket- und Repositoryberechtigungen werden bewusst gekoppelt bzw. explizit freigegeben.

Registry-Credentials folgen dem Secret-Modell aus `docs/51-secret-management.md`.

## Promotion

Ein Image wird einmal gebaut.

```text
Build
  -> Scan
  -> Push nach GHCR
  -> Provenance-Attestation
  -> Development
  -> Staging
  -> Production
```

Staging und Production verwenden denselben Digest. Das Image wird nicht für Production neu gebaut.

## Retention

Die Policy unterscheidet geschützte und bereinigbare Artefakte.

### Immer geschützt

Nicht automatisch löschen:

- Digests, die aktuell in `development`, `staging` oder `main` referenziert sind,
- aktueller Produktions-Digest,
- mindestens zwei vorherige Produktions-Digests als Rollback-Basis.

### Standardaufbewahrung

- Release-Images: 365 Tage,
- Development-Images: 30 Tage,
- Pull-Request-/Preview-Images: 14 Tage,
- ungetaggte und nicht referenzierte Images: 14 Tage.

Vor jeder automatisierten Löschung muss geprüft werden, ob ein Digest noch von einem permanenten Branch, Release oder Rollback-Punkt referenziert wird.

## Cleanup

Cleanup darf nur nicht referenzierte Pakete/Versionen entfernen.

Reihenfolge:

1. Paketversionen und Digests inventarisieren.
2. Referenzen aus `development`, `staging`, `main` und Releases ermitteln.
3. geschützte Rollback-Digests ergänzen.
4. Retention-Regeln auf verbleibende Kandidaten anwenden.
5. Löschkandidaten protokollieren.
6. erst danach löschen.

Die erste v0.5-Version definiert die Policy und Validierung. Eine destruktive automatisierte GHCR-Bereinigung wird bewusst erst eingeführt, wenn der Referenzabgleich als eigener Workflow getestet ist.

## Rollback

Ein Rollback verwendet einen bereits geprüften und weiterhin vorhandenen Digest.

Es wird niemals ein Image mit demselben Tag neu gebaut, um einen alten Zustand zu simulieren.

## Odoo-Ausblick

Für das spätere Odoo-Deployment gilt dasselbe Modell:

- eigene Odoo-/Addon-Images unter `ghcr.io/merchfactory/...`,
- Digest-Pinning,
- Build-Provenance,
- Vulnerability-Scan,
- identischer Digest über Development, Staging und Production.

Offizielle Odoo-, PostgreSQL- oder andere Basisimages werden erst nach expliziter Aufnahme in die Drittanbieter-Allowlist verwendet.

## Referenzen

- `docs/04-security.md`
- `docs/05-cicd.md`
- `docs/06-deployment.md`
- `docs/48-docker-compose-standards.md`
- `docs/51-secret-management.md`
- `configuration/container-image-policy.json`
- GitHub Artifact Attestations für Container Images
- GitHub Container Registry
- Trivy
