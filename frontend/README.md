# Takeoff Tool Frontend

React + TypeScript + Vite application with shadcn/ui and Fabric.js for canvas-based interactions.

## Tech Stack

- **Framework**: React 19 + TypeScript
- **Build Tool**: Vite 7
- **UI Library**: shadcn/ui (New York style)
- **Styling**: Tailwind CSS 3.4
- **Canvas**: Fabric.js 6.9
- **Icons**: Lucide React

## Quick Start

### Local Development

```bash
# Install dependencies
npm install

# Start dev server (http://localhost:5173)
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

### Docker

```bash
# Build and run with docker-compose (from project root)
docker-compose up -d frontend

# Or build standalone
docker build -t takeoff-frontend ./frontend
docker run -p 3000:80 takeoff-frontend
```

## Environment Variables

Create a `.env` file based on `.env.example`:

```bash
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/ws/chat
```

## Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   └── ui/          # shadcn components
│   ├── hooks/           # Custom React hooks (including Fabric.js hooks)
│   ├── lib/
│   │   └── utils.ts     # Utility functions (cn, etc.)
│   ├── App.tsx
│   └── main.tsx
├── Dockerfile           # Multi-stage build (Node → Nginx)
├── nginx.conf          # Nginx config with API/WS proxy
└── components.json     # shadcn configuration
```

## Adding shadcn Components

```bash
npx shadcn@latest add <component-name>
```

## Architecture Notes

- **Fabric.js Logic**: Keep canvas manipulation in custom hooks under `src/hooks/` for testability
- **UI Components**: Use shadcn components from `src/components/ui/`
- **API Communication**: Nginx proxies `/api/` and `/ws/` to backend service in Docker

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Babel](https://babeljs.io/) (or [oxc](https://oxc.rs) when used in [rolldown-vite](https://vite.dev/guide/rolldown)) for Fast Refresh
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/) for Fast Refresh

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the ESLint configuration

If you are developing a production application, we recommend updating the configuration to enable type-aware lint rules:

```js
export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...

      // Remove tseslint.configs.recommended and replace with this
      tseslint.configs.recommendedTypeChecked,
      // Alternatively, use this for stricter rules
      tseslint.configs.strictTypeChecked,
      // Optionally, add this for stylistic rules
      tseslint.configs.stylisticTypeChecked,

      // Other configs...
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
])
```

You can also install [eslint-plugin-react-x](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-x) and [eslint-plugin-react-dom](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-dom) for React-specific lint rules:

```js
// eslint.config.js
import reactX from 'eslint-plugin-react-x'
import reactDom from 'eslint-plugin-react-dom'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...
      // Enable lint rules for React
      reactX.configs['recommended-typescript'],
      // Enable lint rules for React DOM
      reactDom.configs.recommended,
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
])
```
