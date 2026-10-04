# Plain HTML/CSS/JS frontend

Third frontend option. No build step, no framework, just three files. Same backend as the
Streamlit app and the React app.

## Run it

Start the backend first:

```
uvicorn app.api.main:app --reload
```

Then serve this folder with any static file server, for example:

```
cd simple-ui
python -m http.server 5500
```

Open `http://localhost:5500`. Set the backend URL in the sidebar if it is not running on
`http://127.0.0.1:8000`.
