# VoiceSpirit Frontend
This directory contains the React frontend for VoiceSpirit.

## Architecture & Directory Structure
The frontend follows a clean separation of concerns:

- `App.tsx`: Only responsible for assembling components, pages, and hooks. It holds the major layout and routing.
- `hooks/`: Manages all states, side-effects, and direct API communications. The business logic lives here.
- `pages/`: Manages page-level UI. These components take props (usually from hooks) and render the specific views for each feature.
- `components/`: Contains shared, reusable UI elements that are utilized across multiple pages or layouts (e.g., `AppSidebar`, `ErrorNotice`, `VoiceCatalog`).
  - `components/podcast/`: An independent, cohesive feature component group specifically dedicated to the Audio Overview / Podcast workbench UI.
- `test/`: Contains test auxiliary code (e.g., mock implementations, controller factories) to reduce duplicate stubs across component test files.
