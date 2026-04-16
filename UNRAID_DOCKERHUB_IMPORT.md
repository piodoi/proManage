# Docker Hub and Unraid Guide

This repository now publishes Docker images to Docker Hub from Git tags:

- Tags containing `FE` publish the frontend image.
- Tags containing `BE` publish the backend image.

Examples:

- `v1.2.0-FE`
- `v1.2.0-BE`

## GitHub repository settings

Add these GitHub Actions values before creating release tags:

- Secret: `DOCKERHUB_USERNAME`
- Secret: `DOCKERHUB_TOKEN`
- Variable: `DOCKERHUB_NAMESPACE`

The publish jobs run in the GitHub Actions environment named `prod`.

That means you can store the same secret and variable names in `Settings -> Environments -> prod`, and those environment-scoped values will be available to the workflow jobs.

Required names for the `prod` environment:

- Secret: `DOCKERHUB_USERNAME`
- Secret: `DOCKERHUB_TOKEN`
- Variable: `DOCKERHUB_NAMESPACE`

If `DOCKERHUB_NAMESPACE` is not set, the workflow falls back to the GitHub owner for this repo, which is currently `piodoi`.

Optional frontend build variables:

- Variable: `FRONTEND_VITE_API_URL`
- Variable: `FRONTEND_VITE_GOOGLE_CLIENT_ID`
- Variable: `FRONTEND_VITE_FACEBOOK_APP_ID`

You can also store those three values in the `prod` environment instead of repository-level variables.

If `FRONTEND_VITE_API_URL` is not set, the published frontend image is built with:

- `VITE_API_URL=https://api.promanage.urun.me`

## Actual Docker Hub image names

With the current repository owner fallback, the images published are:

- `piodoi/promanage-frontend:<git-tag>`
- `piodoi/promanage-frontend:latest`
- `piodoi/promanage-backend:<git-tag>`
- `piodoi/promanage-backend:latest`

Examples after pushing tags:

- `git tag v1.2.0-FE && git push origin v1.2.0-FE`
- `git tag v1.2.0-BE && git push origin v1.2.0-BE`

Published images:

- `piodoi/promanage-frontend:v1.2.0-FE`
- `piodoi/promanage-frontend:latest`
- `piodoi/promanage-backend:v1.2.0-BE`
- `piodoi/promanage-backend:latest`

After each successful publish, the workflow keeps:

- `latest`
- the newest 3 tag-based images for that repository

Older tag references are deleted from Docker Hub automatically.

## Unraid import values

### Frontend container

Use these values in Unraid:

- Repository: `piodoi/promanage-frontend:latest`
- Network Type: `bridge`
- Container Port: `80`
- Host Port: `3000` or `80`

Important: the frontend image is static and already contains the API base URL from the GitHub build variable `FRONTEND_VITE_API_URL`. If you want the frontend to call your Unraid-hosted backend, set that variable before pushing the `FE` tag and rebuild the frontend image.

### Backend container

Use these values in Unraid:

- Repository: `piodoi/promanage-backend:latest`
- Network Type: `bridge`
- Container Port: `8000`
- Host Port: `8000`
- AppData volume: `/mnt/user/appdata/promanage/userdata` -> `/userdata`

Recommended environment variables:

- `JWT_SECRET=replace-with-a-long-random-secret`
- `FRONTEND_URL=http://YOUR-UNRAID-IP:3000`
- `CORS_ORIGINS=http://YOUR-UNRAID-IP:3000`

Database examples:

- SQLite: `DATABASE_URL=sqlite:////userdata/promanage.db`
- MySQL: `DATABASE_URL=mysql+pymysql://promanage:YOUR_PASSWORD@YOUR_MYSQL_HOST:3306/promanage`

Optional OAuth values:

- `GOOGLE_CLIENT_ID=...`
- `FACEBOOK_APP_ID=...`
- `FACEBOOK_APP_SECRET=...`

## Suggested Unraid setup order

1. Deploy `piodoi/promanage-backend:latest` first.
2. Add the backend environment variables and the `/userdata` volume.
3. Confirm the backend responds on `http://YOUR-UNRAID-IP:8000/health`.
4. Set `FRONTEND_VITE_API_URL` in GitHub to the URL your frontend should call.
5. Push a new `FE` tag so Docker Hub gets a frontend image built for that backend URL.
6. Deploy `piodoi/promanage-frontend:latest` in Unraid.

## Quick release commands

```bash
git tag v1.2.0-BE
git push origin v1.2.0-BE

git tag v1.2.0-FE
git push origin v1.2.0-FE
```