# 🗺️ GPX Routes Manager

**A mobile-first web app for managing GPS routes with cloud storage and easy sharing.**

---

## 👋 Welcome!

You have a **complete, ready-to-run Django application** for organizing your GPS routes (GPX files) from Garmin, Strava, or any GPS device.

## 🎯 What This Does

Upload GPX files → Get beautiful route maps → Organize with tags → Share with friends

**Key Features:**
- 📱 Mobile-first design (works great on phones!)
- 🗺️ Static thumbnails for list + interactive maps for details
- ☁️ Cloud storage (Backblaze B2 - ~$0.02/month for 100 routes)
- 🔖 Tag-based organization
- 🔗 Public sharing via links
- 📤 Single & bulk upload

## 🚀 Get Started in 3 Steps

### Step 1: Install
```bash
chmod +x install.sh
./install.sh
```
This installs all dependencies and sets up the database.

### Step 2: Configure
Edit `.env` with your Backblaze B2 credentials:
```bash
B2_KEY_ID=your-application-key-id
B2_APPLICATION_KEY=your-application-key
B2_BUCKET_NAME=your-bucket-name
```

### Step 3: Run
```bash
python manage.py runserver 0.0.0.0:8000
```

Visit http://localhost:8000 and start uploading routes!

---

## 📚 Documentation

Choose your path:

### 🏃 I Want to Start Now
→ Read **QUICKSTART.md** (5 min read)
- Step-by-step installation
- Basic usage guide
- Troubleshooting

### 🔍 I Want to Understand Everything
→ Read **PROJECT_SUMMARY.md** (10 min read)
- Complete project overview
- Technology stack
- What gets generated
- Customization options

### 📋 I Want All the Details
→ Read **FEATURES.md** (15 min read)
- Every feature explained
- User workflows
- Data models
- Performance characteristics
- Future enhancement ideas

### 📖 Original Documentation
→ Read **README.md**
- The comprehensive original guide
- All specifications
- Detailed technical info

---

## 🎨 What It Looks Like

### Mobile List View
```
┌─────────────────────┐
│ [Map Thumbnail]     │  ← Static PNG, loads fast
│ Mount Tam Loop      │
│ 📍 Mill Valley, CA  │
│ ↔️ 12.5 km ⬆ 450 m │
│ [hiking] [mountains]│
└─────────────────────┘
```

### Desktop Detail View
```
┌─────────────────────────────────────┐
│ [Large Interactive Map]             │  ← Zoom, pan, explore
│ 🟢 Start ─────────── 🔴 End        │
│                                     │
│ 12.50 km | 7.77 mi | 450 m ↑       │
│ Start: Mill Valley, California      │
│ [hiking] [mountains] [california]   │
│ Share: [Copy Link]                  │
└─────────────────────────────────────┘
```

---

## 💡 Quick Tips

**Uploading Routes:**
- Drag & drop GPX files (on desktop)
- Use bulk upload for multiple files
- Names auto-filled from GPX metadata

**Organizing:**
- Add tags during upload or later
- Click tags to filter routes
- Search by route name

**Sharing:**
- Each route gets a unique share link
- Recipients don't need to log in
- Perfect for sharing on social media

**Maps:**
- List view = static images (fast scrolling)
- Detail view = interactive (explore the route)
- Green marker = start, Red marker = end

---

## 🛠️ Tech Stack

| What | Technology |
|------|-----------|
| Backend | Django 6.0 (Python) |
| Frontend | Bootstrap 5 |
| Maps | Folium + OpenStreetMap |
| Storage | Backblaze B2 |
| Database | SQLite (PostgreSQL-ready) |

---

## 📁 Project Structure

```
gpx_routes_project/
├── START_HERE.md          ← You are here!
├── QUICKSTART.md          ← Installation guide
├── PROJECT_SUMMARY.md     ← Complete overview
├── FEATURES.md            ← Detailed features
├── README.md              ← Original docs
│
├── install.sh             ← Run this to install
├── .env.example           ← Config template
├── requirements.txt       ← Python packages
│
├── gpx_routes/            ← Django project
├── routes/                ← Main app
│   ├── models.py          ← Database models
│   ├── views.py           ← View logic
│   ├── utils.py           ← GPX parsing, maps
│   └── templates/         ← HTML files
│
└── manage.py              ← Django commands
```

---

## ✅ Checklist

Before you start:

- [ ] Read QUICKSTART.md
- [ ] Have Backblaze B2 account (free tier works!)
- [ ] Have Python 3.12+ installed
- [ ] Have some GPX files ready to upload

Optional:
- [ ] Install Playwright for nicer thumbnails (recommended)

---

## 🎯 What Happens Next

1. **Install** → Run `install.sh`
2. **Configure** → Add B2 credentials to `.env`
3. **Run** → `python manage.py runserver`
4. **Upload** → Add your first GPX route
5. **Enjoy** → Browse, tag, share your routes!

---

## 🆘 Need Help?

1. **Installation issues?** → See QUICKSTART.md troubleshooting section
2. **Want to customize?** → Check FEATURES.md for customization options
3. **Understanding the code?** → Models, views, and utils are well-commented

---

## 🎉 Ready to Begin?

```bash
# Quick start:
cd gpx_routes_project
./install.sh
# Follow the prompts, then:
python manage.py runserver
```

**Open http://localhost:8000 in your browser!**

---

## 📝 Notes

- **Cost**: ~$0.02/month for 100 routes on Backblaze B2
- **Speed**: 2-5 seconds to process each GPX upload
- **Mobile**: Works great on phones (bottom navigation)
- **Sharing**: Share links require no login
- **Privacy**: Only you can edit, anyone can view shared links

Enjoy your new GPS route manager! 🚀
