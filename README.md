# Waypoint — Project & Task Manager

A small full-stack project/task manager.

- **Backend:** Python (Flask + SQLite) — REST API in `backend/app.py`
- **Frontend:** plain HTML/CSS/JS — `frontend/index.html`, `style.css`, `script.js`
- **Data model:** Projects (routes) contain Tasks (stops), each with a status
  (`todo` / `in_progress` / `done`), a priority (`low` / `medium` / `high`),
  and an optional due date.

## Folder structure

```
waypoint-task-manager/
├── backend/
│   ├── app.py            Flask API + SQLite setup
│   └── requirements.txt
└── frontend/
    ├── index.html
    ├── style.css
    └── script.js
```

## Quick start

1. `cd backend`
2. `python -m venv venv` then activate it
3. `pip install -r requirements.txt`
4. `python app.py` → API runs at `http://127.0.0.1:5000`
5. Open `frontend/index.html` in a browser (or serve it with VS Code's
   "Live Server" extension)

The frontend is hard-coded to call the API at `http://127.0.0.1:5000/api`
(see `API_BASE` at the top of `script.js`) — change that if you run the
backend on a different host or port.

## API reference

| Method | Path                              | Purpose                     |
|--------|-----------------------------------|------------------------------|
| GET    | /api/health                       | Check the API is up          |
| GET    | /api/projects                     | List projects + task counts  |
| POST   | /api/projects                     | Create a project             |
| PUT    | /api/projects/<id>                | Rename / update a project    |
| DELETE | /api/projects/<id>                | Delete a project + its tasks |
| GET    | /api/projects/<id>/tasks          | List a project's tasks       |
| POST   | /api/tasks                        | Create a task                |
| PUT    | /api/tasks/<id>                   | Update a task (incl. status) |
| DELETE | /api/tasks/<id>                   | Delete a task                |

## Ideas to extend it

- Drag-and-drop cards between columns instead of the status dropdown
- User accounts / login so each person has their own routes
- Due-date reminders or an "overdue" badge on cards
- Search across tasks
- Export a project's tasks to CSV
