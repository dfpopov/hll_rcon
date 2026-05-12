import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import HomePage from './pages/HomePage'
import RecordsPage from './pages/RecordsPage'
import PlayerDetailPage from './pages/PlayerDetailPage'

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/records" element={<RecordsPage />} />
        <Route path="/player/:steamId" element={<PlayerDetailPage />} />
      </Routes>
    </Layout>
  )
}
