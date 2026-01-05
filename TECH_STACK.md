# Tech Stack Documentation

## Frontend Technologies

### React 18.2.0
- **Purpose**: UI library for building interactive user interfaces
- **Why**: Component-based architecture, efficient rendering, large ecosystem
- **Usage**: All UI components, state management, routing

### Vite 5.0.8
- **Purpose**: Build tool and development server
- **Why**: Fast HMR (Hot Module Replacement), optimized builds, modern tooling
- **Usage**: Development server, production builds, module bundling

### Chart.js 4.4.0
- **Purpose**: Charting library for data visualization
- **Why**: Easy to use, customizable, responsive charts
- **Usage**: Pie charts for expense analytics

### react-chartjs-2 5.2.0
- **Purpose**: React wrapper for Chart.js
- **Why**: Seamless integration with React components
- **Usage**: ExpensePieChart component

### CSS3
- **Purpose**: Styling and layout
- **Features**: RTL support, responsive design, modern CSS features
- **Usage**: All visual styling, animations, responsive breakpoints

## Backend Technologies

### Node.js
- **Purpose**: JavaScript runtime environment
- **Why**: Same language as frontend, large ecosystem, async I/O
- **Version**: Latest LTS (v24.12.0)

### Express 4.18.2
- **Purpose**: Web application framework
- **Why**: Minimal, flexible, widely used, middleware support
- **Usage**: RESTful API endpoints, request handling, middleware

### MongoDB 6.3.0
- **Purpose**: NoSQL database
- **Why**: Flexible schema, JSON-like documents, easy scaling
- **Usage**: Storing children data and transactions

### CORS 2.8.5
- **Purpose**: Cross-Origin Resource Sharing middleware
- **Why**: Allow frontend (Vercel) to call backend (Railway)
- **Usage**: Enable API access from different origins

### dotenv 16.3.1
- **Purpose**: Environment variable management
- **Why**: Secure configuration, separate dev/prod settings
- **Usage**: Loading MongoDB URI and PORT from environment

## Deployment Platforms

### Vercel
- **Purpose**: Frontend hosting and deployment
- **Features**: 
  - Automatic deployments from GitHub
  - Global CDN
  - Environment variables
  - Preview deployments
- **Plan**: Free tier (sufficient for this project)

### Railway
- **Purpose**: Backend hosting and deployment
- **Features**:
  - Automatic deployments from GitHub
  - Environment variables
  - Logs and monitoring
  - Custom domains
- **Plan**: Paid (required for Node.js services)

### MongoDB Atlas
- **Purpose**: Cloud database hosting
- **Features**:
  - Managed MongoDB
  - Automatic backups
  - Network security
  - Free tier (512MB)
- **Plan**: Free M0 cluster

## Development Tools

### Git
- **Purpose**: Version control
- **Usage**: Code versioning, collaboration

### GitHub
- **Purpose**: Code repository and collaboration
- **Usage**: Source code hosting, CI/CD triggers

### concurrently 8.2.2
- **Purpose**: Run multiple npm scripts simultaneously
- **Usage**: Development (run frontend + backend together)

## Package Management

- **npm** - Node Package Manager
- **package.json** - Dependency management
- **package-lock.json** - Locked dependency versions

## Build Tools

- **Vite** - Frontend bundler and dev server
- **ESBuild** - Fast JavaScript bundler (used by Vite)
- **Node.js** - Backend runtime

## Browser Support

- Modern browsers (Chrome, Firefox, Safari, Edge)
- RTL (Right-to-Left) support for Hebrew
- Responsive design (mobile, tablet, desktop)

## API Communication

- **RESTful API** - Standard HTTP methods (GET, POST)
- **JSON** - Data exchange format
- **CORS** - Cross-origin requests enabled
- **Error Handling** - HTTP status codes and error messages

## Data Storage

- **Primary**: MongoDB Atlas (cloud)
- **Fallback**: In-memory storage (development/testing)
- **Session Storage**: Browser sessionStorage for login state

## Security Features

- Password protection for parent dashboard
- Session-based authentication
- Input validation (server-side)
- CORS configuration
- MongoDB network access restrictions

## Performance Optimizations

- Auto-refresh intervals (5 seconds for child views)
- Efficient database queries
- CDN for static assets (Vercel)
- Optimized React rendering

## Monitoring & Logging

- **Railway**: Application logs
- **Vercel**: Build logs and function logs
- **MongoDB Atlas**: Database metrics
- **Console Logging**: Server-side error tracking

---

**Documentation Version**: 1.0  
**Last Updated**: December 2024

