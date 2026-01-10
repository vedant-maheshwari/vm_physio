# How to Deploy VriddhaMitra

You asked how to show this to other people for a demo. Here are two ways: one for a **Quick Demo** from your laptop, and one for **24/7 Free Hosting**.

## Option A: Quick Demo with ngrok (Recommended for "Right Now")
This runs the app on your laptop but gives you a public URL (like `https://xyz.ngrok-free.app`) to share with anyone.

### Steps:
1.  **Install ngrok**:
    -   Go to [ngrok.com/download](https://ngrok.com/download) and sign up for a free account.
    -   Follow their install instructions (e.g., `brew install ngrok/ngrok/ngrok` on Mac).
    -   Connect your account: `ngrok config add-authtoken <YOUR_TOKEN>`

2.  **Start your Backend**:
    -   Open a terminal in the project folder and run:
        ```bash
        uvicorn app:app --port 8000
        ```

3.  **Start the Tunnel**:
    -   Open a **new** terminal tab/window.
    -   Run:
        ```bash
        ngrok http 8000
        ```

4.  **Share**:
    -   Copy the `https://...` URL shown in the terminal.
    -   Send that link to anyone. They can open it on their phone or laptop!

---

## Option B: Free Hosting on Render (24/7 Access)
Use this if you want the app to keep working even when your laptop is closed.

### Steps:
1.  **Push Code to GitHub**:
    -   Create a new repo on GitHub.
    -   Push your `VriddhaMitra` code to it.
2.  **Create Account on Render.com**:
    -   Sign up with GitHub.
3.  **New Web Service**:
    -   Click "New +" -> "Web Service".
    -   Select your repository.
4.  **Configure**:
    -   **Runtime**: Python 3
    -   **Build Command**: `pip install -r requirements.txt`
    -   **Start Command**: `uvicorn app:app --host 0.0.0.0 --port 10000`
5.  **Environment Variables**:
    -   Add `JWT_SECRET_KEY` = (generate a random string)
    -   Add `DATABASE_URL` = `sqlite:///./vriddhamitra.db` (Note: SQLite on Render resets when the app restarts on the free tier. For persistent data, use Render's PostgreSQL).

---

## Option C: PythonAnywhere (Best for Permanent Data)
**Recommended for Pilot Testing**: Unlike Render's free tier, **PythonAnywhere** keeps your SQLite database file forever, so you won't lose patient data when the server restarts.

### Steps:
1.  **Sign Up**:
    -   Go to [www.pythonanywhere.com](https://www.pythonanywhere.com/) and create a "Beginner" (Free) account.
2.  **Upload Code**:
    -   Go to the "Files" tab.
    -   Upload your project files (app.py, requirements.txt, static folder, etc.) or use the "Bash" console to `git clone` your repo.
3.  **Install Dependencies**:
    -   Open a "Bash" console.
    -   Run: `pip3.10 install -r requirements.txt` (or appropriate python version).
4.  **Configure Web App**:
    -   Go to "Web" tab -> "Add a new web app".
    -   Choose **FastAPI** (if available) or "Manual Configuration" -> Python 3.10.
    -   In "WSGI configuration file", you will need to adapt it for FastAPI (PythonAnywhere uses WSGI by default, but Uvicorn is needed).
    -   *Simpler Alternative*: Just run it in the console!
        -   Open a Bash console.
        -   Run `uvicorn app:app --host 0.0.0.0 --port 8000`
        -   Note: The free tier might restrict ports. For proper hosting, use the Web tab configuration with an ASGI adapter or sticking to the Flask/WSGI standard if you were using Flask. Since we are using FastAPI, Render is often easier, but for persistent storage on PythonAnywhere, you might need a bit more setup.

### **Why not Netlify?**
You asked about **Netlify**. Netlify is amazing for *static websites* (HTML, CSS only) but **cannot run Python backend code** (like `app.py`) easily. Since your app needs a database and Python logic to save patients/notes, Netlify will not work.

**Summary for Pilot:**
1.  **ngrok**: Easiest. Runs on your laptop. Free.
2.  **Render**: Good cloud hosting. Free. (Data might reset on restart).
3.  **PythonAnywhere**: Good for data persistence. Free.

## Mobile App (PWA)
I have converted your web app into a **Progressive Web App (PWA)**!

**How to Install on Phone:**
1.  Open your deployed URL (ngrok or Render) on Safari (iOS) or Chrome (Android).
2.  **iOS**: Tap the "Share" button -> "Add to Home Screen".
3.  **Android**: Tap the "Three Dots" menu -> "Install App" or "Add to Home Screen".
4.  It will appear as a real app icon (VriddhaMitra) on your home screen!
