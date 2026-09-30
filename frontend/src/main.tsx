import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { CompetitionList } from './pages/CompetitionList'
import './styles.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <CompetitionList />
  </StrictMode>,
)
