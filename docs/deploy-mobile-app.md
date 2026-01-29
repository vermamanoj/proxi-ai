 # Mobile App Deployment (Android)

**Builds the Proxi Android APK from frontend code.**

---

## Prerequisites

- **Android Studio** installed (provides Java JDK)
- **Node.js** 20.x+
- **Java path:** `e:\Program Files\Android\Android Studio\jbr`

---

## Full Workflow

### 1. Ensure API Key for Voice

Voice mode requires the Gemini API key embedded at build time:

```powershell
# Check/create frontend/.env
cd E:\data\proxi-ai\frontend
if (!(Test-Path .env)) {
    $key = (Get-Content "..\..\.env" | Select-String "GEMINI_API_KEY").Line.Split('=')[1]
    "VITE_GEMINI_API_KEY=$key" | Out-File .env -Encoding UTF8
}
```

### 2. Build Frontend for Capacitor

```powershell
cd E:\data\proxi-ai\frontend
$env:CAPACITOR_BUILD='true'; npm run build
```

### 3. Sync to Android

```powershell
npx cap sync android
```

### 4. Build APK

```powershell
cd android
$env:JAVA_HOME = "e:\Program Files\Android\Android Studio\jbr"
.\gradlew assembleDebug
```

### 5. Locate APK

```powershell
Get-Item "E:\data\proxi-ai\frontend\android\app\build\outputs\apk\debug\app-debug.apk" | Select-Object FullName, Length, LastWriteTime
```

**APK Path:** `E:\data\proxi-ai\frontend\android\app\build\outputs\apk\debug\app-debug.apk`

---

## Install on Device

**Via ADB:**
```powershell
adb install -r "E:\data\proxi-ai\frontend\android\app\build\outputs\apk\debug\app-debug.apk"
```

**Manual:** Transfer APK to phone and install (enable "Unknown sources")

---

## One-Liner (After Initial Setup)

```powershell
cd E:\data\proxi-ai\frontend; $env:CAPACITOR_BUILD='true'; npm run build; npx cap sync android; cd android; $env:JAVA_HOME="e:\Program Files\Android\Android Studio\jbr"; .\gradlew assembleDebug
```

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `JAVA_HOME not set` | Set `$env:JAVA_HOME` before gradlew |
| Voice not working | Ensure `frontend/.env` has `VITE_GEMINI_API_KEY` |
| Build fails | Run `npm install` in frontend first |

---

*See also: [MOBILE_STRATEGY.md](./MOBILE_STRATEGY.md) for Capacitor setup details*