import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import './index.css'
import * as serviceWorker from './utils/serviceWorker'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)

// Register service worker for production caching
if (process.env.NODE_ENV === 'production') {
  serviceWorker.register({
    onSuccess: () => {
      console.log('Content cached for offline use');
    },
    onUpdate: () => {
      console.log('New content available, please refresh');
    }
  });
}