# VyomPath — Step-by-Step Free Public Deployment Guide

> **Target Platform:** Render (Free Tier — $0.00 / No Credit Card Required)  
> **Application:** VyomPath (NASA Space Apps Challenge 2026)  
> **Repository:** `MayankSharma-2812/vyompath-spaceapps-2026`  
> **Target Branch:** `main` (Commit `0d9ef51`)  
> **Estimated Setup Time:** ~10 minutes

---

## 1. Accounts and Prerequisites

To deploy VyomPath publicly for free, you only need two free accounts:

1. **GitHub Account:**  
   - URL: [https://github.com/signup](https://github.com/signup)  
   - Purpose: Hosts the canonical VyomPath repository.  
   - Cost: **$0.00** (Free). No credit card required.
2. **Render Account:**  
   - URL: [https://render.com](https://render.com) (Click "Sign Up" $\to$ "Sign in with GitHub")  
   - Purpose: Hosts the FastAPI backend (Free Web Service) and React frontend (Free Static Site).  
   - Cost: **$0.00** (Free). **No credit card required** for free web services or static sites.

---

## 2. Prepare the GitHub Repository

1. Open your browser and navigate to your canonical repository:  
   `https://github.com/MayankSharma-2812/vyompath-spaceapps-2026`
2. Confirm that the default branch is **`main`** and contains the latest verified commit (`0d9ef51`).
3. Ensure the repository visibility is set to **Public** (required for Render free-tier repository connections).
4. Verify that no private data files or untracked scratch notes (`decision.md`) are present.

---

## 3. Step 1: Deploy the FastAPI Backend (Render Web Service)

Deploy the backend first so you have its public URL ready before configuring the frontend.

1. Log into your **Render Dashboard** ([dashboard.render.com](https://dashboard.render.com/)).
2. Click the blue **"New +"** button in the top navigation bar and select **"Web Service"**.
3. Under **"Connect a repository"**, select your GitHub repository:  
   `MayankSharma-2812/vyompath-spaceapps-2026`.
4. Fill in the service configuration with these **exact values**:

| Setting | Exact Value to Enter | Notes |
|---|---|---|
| **Name** | `vyompath-api` | Your backend URL will be `https://vyompath-api.onrender.com`. |
| **Region** | `Frankfurt (EU Central)` or `Oregon (US West)` | Select the region closest to your audience. |
| **Branch** | `main` | Production branch. |
| **Root Directory** | *(Leave blank)* | Uses repository root. |
| **Runtime** | `Python 3` | Native Python runtime. |
| **Build Command** | `pip install -r backend/requirements.txt` | Installs FastAPI, Uvicorn, Pydantic, Rasterio, Pyproj. |
| **Start Command** | `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT --workers 1` | Binds to Render's dynamic `$PORT`. |
| **Instance Type** | **Free** ($0 / month) | 512 MB RAM, 0.1 CPU. |

5. Scroll down to **"Advanced"** and click **"Add Environment Variable"**:

| Key | Value |
|---|---|
| `PYTHON_VERSION` | `3.12.0` |
| `CORS_ORIGINS` | `*` *(or update to your frontend URL once created)* |
| `VYOMPATH_DEM_PATH` | *(Leave empty)* |

> **Scientific Data Note (Mock vs Real DTM Mode):**  
> On Render's free tier, persistent disk storage is not supported. Leaving `VYOMPATH_DEM_PATH` empty enables **`development/mock` mode**, which consumes only ~60 MB RAM, boots instantly, and provides full mathematical transparency for judge evaluation. The full Float32 HiRISE DTM raster (121 MB) is demonstrated locally using `run_offline.sh`.

6. Click **"Deploy Web Service"**.
7. Wait 2–3 minutes for the build to finish. Once you see **"Your service is live 🎉"**, copy your backend URL:  
   **`https://vyompath-api.onrender.com`**

---

## 4. Step 2: Deploy the React Frontend (Render Static Site)

Render Static Sites are **100% free**, offer unlimited bandwidth, have **zero cold starts**, and are distributed across a global CDN.

1. In your **Render Dashboard**, click **"New +"** and select **"Static Site"**.
2. Select your repository: `MayankSharma-2812/vyompath-spaceapps-2026`.
3. Fill in the static site configuration with these **exact values**:

| Setting | Exact Value to Enter | Notes |
|---|---|---|
| **Name** | `vyompath` | Your public URL will be `https://vyompath.onrender.com`. |
| **Branch** | `main` | Production branch. |
| **Root Directory** | `frontend` | Points to the frontend directory. |
| **Build Command** | `npm install && npm run build` | Compiles Vite production bundle. |
| **Publish Directory** | `dist` | Path relative to Root Directory (`frontend/dist`). |

4. Scroll down to **"Advanced"** and click **"Add Environment Variable"**:

| Key | Value | Notes |
|---|---|---|
| `VITE_API_URL` | `https://vyompath-api.onrender.com` | **Crucial:** Points browser API requests to your live backend. |

5. Scroll to **"Redirects/Rewrites"** and click **"Add Rule"** (ensures client-side routing works on page refresh):
   - **Type:** `Rewrite`
   - **Source:** `/*`
   - **Destination:** `/index.html`

6. Click **"Deploy Static Site"**.
7. Wait ~1 minute. When the build completes, your public website will be live at:  
   **`https://vyompath.onrender.com`**

---

## 5. Step 3: Connect and Harden CORS

Now that your frontend URL is live, restrict the backend CORS origins for production security:

1. In Render Dashboard, click on your **`vyompath-api`** service.
2. Go to **"Environment"**.
3. Edit the `CORS_ORIGINS` variable:
   - **Key:** `CORS_ORIGINS`
   - **Value:** `https://vyompath.onrender.com,http://localhost:8080,http://localhost:5173`
4. Click **"Save Changes"**. Render will automatically redeploy the backend in ~30 seconds.

---

## 6. Verification Checklist (12 Sequential Checks)

Run these checks to confirm that your public deployment is fully functional:

| Step | Action | Expected Result |
|:---:|---|---|
| **1** | Open `https://vyompath-api.onrender.com/api/health` in a browser. | Returns JSON: `{"status":"ok","mode":"development/mock",...}`. |
| **2** | Open `https://vyompath-api.onrender.com/docs`. | Interactive Swagger UI documentation loads with `/api/health`, `/api/layers`, `/api/routes/analyze`. |
| **3** | Open `https://vyompath.onrender.com` in an incognito window. | The Mars Research Workspace dashboard loads with branding and sidebar navigation. |
| **4** | Check the top toolbar status badge. | Displays **`DEVELOPMENT / MOCK BACKEND`** (truthfully disclosing demo mode). |
| **5** | Inspect the Mars Map Canvas. | Mars equirectangular map renders with Jezero Crater centered. |
| **6** | Switch Base Layers. | Dropdown switches between MOLA Color Relief, CTX Visible Mosaic, and Viking MDIM 2.1. |
| **7** | Click preset corridor **"Floor Corridor (Sol 386–387)"**. | Map draws the traverse and submits analysis to `https://vyompath-api.onrender.com/api/routes/analyze`. |
| **8** | Inspect Terrain Elevation Profile. | Chart plots elevation curve with Min/Max Elevation, Gain, and Loss cards populated. |
| **9** | Click **"Pin Current as Route B"**. | Pinned Route B card appears with side-by-side KPI comparison and descriptive deltas ($\Delta$). |
| **10** | Test Sidebar Navigation buttons. | Clicking "Terrain Profile", "Route Comparison", or "Data Sources" smoothly scrolls the viewport to that panel. |
| **11** | Open Developer Tools Console (`F12`). | **0 console errors**; network tab confirms successful `POST /api/routes/analyze` returning HTTP 200. |
| **12** | Refresh the page (`F5`). | SPA routing handles reload cleanly without 404 errors. |

---

## 7. Free-Tier Limitations & Scientific Honesty

| Dimension | Render Free Tier Limits | Impact on VyomPath |
|---|---|---|
| **Cost** | **$0.00 / forever** | Completely free; no credit card required. |
| **Cold Starts** | Backend spins down after 15 min of inactivity. | The first API request after 15 minutes takes **~40–50 seconds** to wake up. Once awake, requests respond in $<100\text{ ms}$. |
| **Frontend CDN** | **Zero cold starts** | The static site is served from Render's global CDN and loads instantly at all times. |
| **RAM & CPU** | 512 MB RAM / 0.1 CPU | FastAPI in mock mode uses only ~60 MB RAM (well within limits). |
| **Real DTM Storage** | Ephemeral storage only (no free disk volumes). | Real Float32 HiRISE DTM (121 MB) is not hosted on Render free tier. Deployed instance runs in `development/mock` mode. |
| **Scientific Disclosure** | Top toolbar badge shows `DEVELOPMENT / MOCK`. | Prevents misrepresenting synthetic results as real data. Real DTM is evaluated locally via offline scripts. |

---

## 8. Troubleshooting Common Deployment Issues

### Issue 1: Backend build fails on Rasterio / GDAL
- **Root Cause:** Trying to compile GDAL from source on an incompatible Python version.
- **Solution:** In Render backend settings, ensure `PYTHON_VERSION` is set to `3.12.0`. Pre-compiled manylinux wheels for Rasterio install in $<15\text{ seconds}$.

### Issue 2: Frontend shows "Unable to load elevation data"
- **Root Cause:** The backend was sleeping, or `VITE_API_URL` was not configured during frontend build.
- **Solution:** 
  1. Open `https://vyompath-api.onrender.com/api/health` directly in your browser to wake the backend container.
  2. In your Render Static Site settings, verify `VITE_API_URL` is set to `https://vyompath-api.onrender.com`.
  3. Click **"Manual Deploy" $\to$ "Deploy latest commit"** on the frontend to re-bake the environment variable into the bundle.

### Issue 3: Page refresh gives 404 Not Found
- **Root Cause:** Missing SPA fallback rewrite rule in Nginx/CDN.
- **Solution:** In Render Static Site $\to$ **Redirects/Rewrites**, add a rewrite rule from `/*` to `/index.html`.

---

## 9. Final Deployment Checklist

- [ ] GitHub repository is public on `main` branch.
- [ ] Render account created using GitHub login (no credit card entered).
- [ ] Backend Web Service `vyompath-api` deployed and reports `status: ok` on `/api/health`.
- [ ] Frontend Static Site `vyompath` deployed with `VITE_API_URL` pointing to backend.
- [ ] SPA rewrite rule (`/*` $\to$ `/index.html`) saved.
- [ ] Backend `CORS_ORIGINS` updated with live frontend domain.
- [ ] All 12 verification checks passed in an incognito browser window.
- [ ] Public URL (`https://vyompath.onrender.com`) submitted to NASA Space Apps portal.
