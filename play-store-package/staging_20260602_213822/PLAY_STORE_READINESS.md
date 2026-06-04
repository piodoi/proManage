# Google Play Readiness

This repository is not yet ready for direct Google Play submission.

## What exists already

- Web frontend build pipeline in `frontend/package.json`
- Web app manifest in `frontend/public/manifest.json`
- App icon source in `frontend/public/icon.png`
- Privacy policy page in `frontend/src/pages/PrivacyPolicy.tsx`
- Terms page in `frontend/src/pages/TermsOfService.tsx`
- Capacitor config scaffold in `frontend/capacitor.config.ts`
- Play asset workspace in `frontend/play-store-assets/`

## What is missing for Google Play

### Required app package

- Android Studio project still needs to be generated and synced
- No signed `.aab` exists yet
- No release keystore/signing config exists yet

### Required Play Console assets

- App screenshots are missing
- 1024x500 feature graphic is missing
- Play icon asset set is missing as a dedicated store package
- Optional promo video link is not prepared

### Required policy and account items

- Public production privacy policy URL must be confirmed
- Public production terms URL should be confirmed
- Account deletion URL and flow should be documented for Play review
- Data safety questionnaire answers are not prepared
- Content rating questionnaire answers are not prepared

### Recommended PWA/mobile quality items

- No service worker is registered, so offline/installability is incomplete
- No Android deep-link/app-link verification setup exists
- No push notification permission flow for Android exists

## Recommended path

### Fastest practical route

1. Use the included Capacitor scaffold and generate an Android project.
2. Build a signed Android App Bundle (`.aab`).
3. Prepare Play listing assets and policy URLs.

### Alternative route

1. Convert the web app into a production-grade PWA with service worker and origin verification.
2. Package it as a Trusted Web Activity.
3. Build and sign the resulting Android App Bundle.

## Minimum submission checklist

- Signed Android App Bundle (`.aab`)
- Application ID / package name
- Privacy policy URL
- Account deletion instructions or deletion URL
- 1 app icon for Play listing
- Phone screenshots
- 7-inch tablet screenshots if tablet support is declared
- 10-inch tablet screenshots if tablet support is declared
- Feature graphic 1024x500
- Short description
- Full description
- Support email
- Developer contact details
- Data safety form answers
- Content rating form answers
- Target audience declaration

## Repo-specific note

The repository now contains the Capacitor config and Play asset workspace. The next concrete implementation step is generating the Android shell and producing a first debug Android build.