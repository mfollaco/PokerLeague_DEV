# PokerLeague_DEV Phase 2 Roadmap
Game Night Operations Platform

Last updated: 2026-03-08

---

# Overview

Phase 2 transforms PokerLeague_DEV from a **league analytics website** into a **live game-night operating system**.

Phase 1 focuses on:
- analytics
- historical insights
- league storytelling
- season reports

Phase 2 focuses on:
- running the actual tournament night
- capturing structured data live
- feeding analytics automatically
- creating a mobile-first operational app

This phase is expected to begin **after the Phase 1 multi-season architecture is complete**.

---

# Core Vision

The PokerLeague platform becomes the **control center for the entire poker night**.

Instead of manually recording results and later importing them, the system will:

1. Run the **tournament timer**
2. Track **blind levels and breaks**
3. Capture **player eliminations**
4. Track **finish order automatically**
5. Store **structured event data**
6. Feed the **Phase 1 analytics pipeline**

The result:

Game Night → Structured Data → Analytics

No manual cleanup required.

---

# Phase 2 Architecture Goals

The system must support:

• Mobile-friendly operation  
• Touch-optimized UI  
• Reliable timer behavior  
• Fast event entry during gameplay  
• Persistent data capture  
• Clean integration with analytics pipeline  

Future considerations:

• Progressive Web App (PWA)  
• Native mobile app potential  
• Commissioner/operator mode  
• Display mode for TV or large screen  

---

# Phase 2 Development Stages

---

# Phase 2A — Game Night Workflow Design

Before writing code, define the **actual game night workflow**.

Key questions:

What happens in order on a typical poker night?

Example flow:

1. Commissioner opens game-night app
2. Selects season and event
3. Players check in
4. Seating is confirmed
5. Timer begins
6. Blind levels advance
7. Players bust out
8. Eliminations are recorded
9. Final placements are determined
10. Event closes and exports results

---

## Define required screens

Potential screens:

### Game Setup
- select season
- create event
- choose blind schedule
- set start stack

### Player Check-in
- mark players present
- assign seats (optional)

### Tournament Timer
- blind level timer
- break timer
- next level preview

### Elimination Entry
- select eliminated player
- optionally select who eliminated them
- automatic placement tracking

### Standings
- remaining players
- bust order
- final rankings

### Event Summary
- final results
- payouts
- export / save

---

# Phase 2B — MVP Game Night System

First operational version.

This version should focus on **core functionality only**.

Features:

### Tournament Timer
- blind level countdown
- automatic level progression
- pause/resume
- break support

### Player List
- registered players
- active vs eliminated

### Elimination Logging
- record player bust
- record killer (optional)
- timestamp event

### Automatic Placement Tracking
- determine finishing order
- identify winner
- calculate final standings

### Data Output
Structured export compatible with Phase 1 pipeline.

Possible formats:
- JSON
- direct database write
- ingestion file for analytics pipeline

---

# Phase 2C — Integrated League Platform

Later expansion once MVP works reliably.

Possible features:

### Commissioner Dashboard
- season management
- event creation
- player management

### Live Display Mode
For TV or tablet during the game.

Display:
- timer
- blind levels
- remaining players
- chip-and-chair scenarios
- current leaderboards

### Player Profiles
- personal stats
- rivalries
- elimination history

### Authentication
- commissioner role
- player accounts (optional)

### Cloud Sync
- persistent storage
- multi-device operation

---

# Data Model Considerations

Live event capture must support:

Event data such as:

- event_id
- season_id
- player_id
- elimination_time
- eliminated_player
- killer_player
- level
- remaining_players

These events should be structured so they can directly power analytics.

---

# Integration With Phase 1

Phase 2 must produce data compatible with the existing analytics system.

Examples:

EliminationsPairCounts  
Survival data  
Finish order  
WeeklyPoints  
SeasonTotals  

The Phase 2 system should eventually **generate these datasets automatically**.

---

# Technical Direction (Early Thoughts)

Possible stack directions:

Frontend:
- React / Next.js
- or modern JS framework

Mobile:
- Progressive Web App
- installable on phones

Timer reliability:
- background-safe timer logic
- local state persistence

Storage options:

Early stage:
- local storage
- JSON export

Later:
- SQLite / Postgres
- API service

---

# MVP Success Criteria

Phase 2 MVP is successful when:

• The timer runs the tournament  
• Eliminations are captured live  
• Final placements are correct  
• Data exports cleanly  
• Analytics can ingest the results without manual cleanup  

---

# Long-Term Vision

PokerLeague becomes a **complete league platform**:

Game Night Operations  
+  
Analytics Engine  
+  
Historical League Intelligence

Possible future expansions:

• Live game dashboards  
• Rivalry timelines  
• Player improvement tracking  
• Dynasty metrics  
• Multi-league support

---

# Phase 2 Status

Not started.

Prerequisite:
Finish Phase 1 multi-season architecture.

