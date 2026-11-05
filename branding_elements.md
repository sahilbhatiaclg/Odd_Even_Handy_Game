# Branding Elements & Color Palette: Odd-Even Hand Cricket

This document defines the visual identity, color tokens, and element mapping for the **Odd-Even Hand Cricket** game. It serves as a master design reference for building end-to-end pages, UI components, and game screens.

---

## 1. Primary Player Colors (From the Uploaded Screenshot)

The screenshot highlights the two opposing player badges in the scoreboard:

| Element | Color Preview | Hex Code | RGB | CSS Source / Class | Where it is used in the game |
| :--- | :---: | :---: | :---: | :--- | :--- |
| **Player 1 Name Tag ("Sahil")**<br>*(Base Primary Blue)* | `🟦` | `#3D6FE0` | `rgb(61, 111, 224)` | `var(--blue)`<br>`.nametag.p0` | • **Player 1 ("Host") Name Badge** on scoreboard<br>• Game title in header (`.logo h1`, `.topbar .name`)<br>• Match phase indicators (`.phase`)<br>• "Join Room" & "Bowl First" buttons (`.btn-blue`) |
| **Player 1 (Inactive / Disconnected)**<br>*(Rendered in Image)* | `🩵` | `#9EB7EF` | `rgb(158, 183, 239)` | `.player.off .nametag.p0`<br>*(50% opacity over white)* | • Appears when Player 1 is temporarily disconnected or waiting to reconnect |
| **Player 2 Name Tag ("Rudra")**<br>*(Opponent / Primary Accent)* | `🟧` | `#FF8A3D` | `rgb(255, 138, 61)` | `.nametag.p1` | • **Player 2 ("Guest") Name Badge** on scoreboard<br>• High-contrast differentiator distinguishing player 1 from player 2 |

---

## 2. Complete Design System & Palette Table

| Token / Color Name | Hex Code | RGB | Swatch | Usage / Element in Game |
| :--- | :--- | :--- | :---: | :--- |
| **Primary Blue** | `#3D6FE0` | `rgb(61, 111, 224)` | 🟦 | Header title, Player 1 badge, Action buttons, Game phase titles |
| **Player 2 Orange** | `#FF8A3D` | `rgb(255, 138, 61)` | 🟧 | Player 2 name badge, opposing team highlight |
| **Page / Card Background** | `#FFFFFF` | `rgb(255, 255, 255)` | ⬜ | Main page canvas, game card background, input fields, unselected number buttons |
| **Line & Ink (Solid Black)** | `#1B1B1B` | `rgb(27, 27, 27)` | ⬛ | Card borders (`3px solid`), button shadows (`box-shadow`), score numbers (`.score`), animated waiting dots |
| **Muted Grey** | `#6B6B6B` | `rgb(107, 107, 107)` | 🩶 | "ODD / EVEN - YOU" tags, subheadings, labels, instructions |
| **Canary Yellow** | `#FFD23F` | `rgb(255, 210, 63)` | 🟨 | **Room Code Box** (`.codebox`), **Selected Number Button** (`.selected`), **Bowling Role Badge** (`.role.bowl`), input focus ring |
| **Pitch Green** | `#4CC72F` | `rgb(76, 199, 47)` | 🟩 | **"Create Room" Button** (`.btn-green`), **"Bat First" Button**, **Batting Role Badge** (`.role.bat`), Match Win message (`.verdict.win`) |
| **Wicket Red** | `#E5413C` | `rgb(229, 65, 60)` | 🟥 | **Timer Warning** (when $\le 3$s), **OUT Verdict** (`.verdict.out`), **Target Score Display**, error messages |
| **Neutral Button Grey** | `#EEEEEE` | `rgb(238, 238, 238)` | 🔘 | Default button background before interaction |

---

## 3. Element-by-Element Location Guide

### A. Lobby / Home Page (`index.html`)
* **Logo (`.logo h1`)**:
  * Word *"Odd-Even"*: `#3D6FE0` (Primary Blue)
  * Word *"Hand Cricket"*: `#1B1B1B` (Ink Black)
* **Input Fields (`input`, `select`)**:
  * Background: `#FFFFFF`
  * Border: `2px solid #1B1B1B`
  * Focus Outline: `3px solid #FFD23F` (Canary Yellow)
* **Buttons**:
  * "Create room" button: `#4CC72F` (Pitch Green) with solid black 3D shadow (`box-shadow: 0 4px 0 #1B1B1B`)
  * "Join room" button: `#3D6FE0` (Primary Blue) with white text

### B. Game Room & Top Bar (`game.html`)
* **Header Title**: `#3D6FE0` (Primary Blue)
* **Room Code Display (`.codebox`)**:
  * Background: `#FFD23F` (Canary Yellow)
  * Border: `2px solid #1B1B1B`
  * Text: Bold monospace black text

### C. Scoreboard Card (`.scoreboard`)
* **Outer Player Box (`.player`)**:
  * White card `#FFFFFF` with `2px solid #1B1B1B` rounded border.
  * Disconnected state (`.player.off`): `opacity: 0.5`.
* **Player 1 Name Pill (`.nametag.p0`)**:
  * Background: `#3D6FE0` (Primary Blue)
  * Text: `#FFFFFF` (White)
* **Player 2 Name Pill (`.nametag.p1`)**:
  * Background: `#FF8A3D` (Tangerine Orange)
  * Text: `#FFFFFF` (White)
* **Role Badges (`.role`)**:
  * Batting (`.role.bat`): `#4CC72F` (Green)
  * Bowling (`.role.bowl`): `#FFD23F` (Yellow)
* **Runs / Score (`.score`)**:
  * Large `#1B1B1B` bold number (`2.2rem`).

### D. Interactive Gameplay Controls
* **Round Timer Box (`.timer span`)**:
  * Normal state: White `#FFFFFF` with `3px solid #1B1B1B` border.
  * Critical countdown ($\le 3$s) (`.low`): `#E5413C` (Wicket Red) background with white digits.
* **Hand-Sign Number Grid (Buttons 1 to 6)**:
  * Unselected buttons: `#FFFFFF` background with `2px solid #1B1B1B` border.
  * Selected number (`.selected`): `#FFD23F` (Canary Yellow) background with `3px solid #1B1B1B` outline.
* **Toss Decision Buttons**:
  * "Bat first": `#4CC72F` (Green)
  * "Bowl first": `#3D6FE0` (Blue)
* **Round Reveal Verdict**:
  * Normal runs: `#1B1B1B`
  * Wicket OUT (`.verdict.out`): `#E5413C` (Red)
  * Match Winner (`.verdict.win`): `#4CC72F` (Green)

---

## 4. CSS Design Tokens (Ready-to-Use Snippet)

Copy and paste this into any stylesheet when styling new pages or redesigning components:

```css
:root {
  /* Canvas & Containers */
  --page-bg: #ffffff;
  --card-bg: #ffffff;
  --line: #1b1b1b;
  --shadow: 4px 4px 0 #1b1b1b;

  /* Typography */
  --ink: #1b1b1b;
  --muted: #6b6b6b;

  /* Primary Branding (Player 1 & 2) */
  --player-1-blue: #3d6fe0;
  --player-1-inactive: #9eb7ef;
  --player-2-orange: #ff8a3d;

  /* Game Accent & State Colors */
  --yellow-accent: #ffd23f;   /* Room code, bowling badge, selected button */
  --green-action: #4cc72f;    /* Create room, bat badge, victory text */
  --red-alert: #e5413c;       /* Timer low, OUT dismissal, errors */
  --grey-button: #eeeeee;     /* Neutral action button */
}

/* Example Player Badges */
.badge-player-1 {
  background: var(--player-1-blue);
  color: #ffffff;
  border: 2px solid var(--line);
  border-radius: 6px;
  padding: 3px 10px;
}

.badge-player-2 {
  background: var(--player-2-orange);
  color: #ffffff;
  border: 2px solid var(--line);
  border-radius: 6px;
  padding: 3px 10px;
}
```

