import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import HomePage from './pages/HomePage'
import RecordsAllTimePage from './pages/RecordsAllTimePage'
import RecordsSingleGamePage from './pages/RecordsSingleGamePage'
import PlayerDetailPage from './pages/PlayerDetailPage'
import AchievementsPage from './pages/AchievementsPage'
import AchievementDetailPage from './pages/AchievementDetailPage'
import ComparePage from './pages/ComparePage'
import HallOfShamePage from './pages/HallOfShamePage'
import WorldMapPage from './pages/WorldMapPage'
import PlaystylesPage from './pages/PlaystylesPage'
import PlaystyleDetailPage from './pages/PlaystyleDetailPage'
import MatchTitlesPage from './pages/MatchTitlesPage'

export default function App() {
  return (
    <Layout>
      <Routes>
        {/* `/` is reserved by the nginx layer for a redirect to `/live/`
            (the current-match page) — see stats_app/nginx.conf. That redirect
            happens at the HTTP level so React Router never sees a real
            request for `/`. The route below is kept so direct in-app
            navigation via React Router (back button after a redirect, an
            old saved tab, …) still lands on the leaderboard instead of a
            blank page. */}
        <Route path="/" element={<Navigate to="/leaderboard" replace />} />
        <Route path="/leaderboard" element={<HomePage />} />
        <Route path="/records" element={<Navigate to="/records/all-time" replace />} />
        <Route path="/records/all-time" element={<RecordsAllTimePage />} />
        <Route path="/records/single-game" element={<RecordsSingleGamePage />} />
        <Route path="/player/:steamId" element={<PlayerDetailPage />} />
        <Route path="/achievements" element={<AchievementsPage />} />
        <Route path="/achievements/:id" element={<AchievementDetailPage />} />
        <Route path="/compare" element={<ComparePage />} />
        <Route path="/compare/:ids" element={<ComparePage />} />
        <Route path="/hall-of-shame" element={<HallOfShamePage />} />
        <Route path="/server/countries" element={<WorldMapPage />} />
        <Route path="/playstyles" element={<PlaystylesPage />} />
        <Route path="/playstyles/:id" element={<PlaystyleDetailPage />} />
        <Route path="/match-titles" element={<MatchTitlesPage />} />
      </Routes>
    </Layout>
  )
}
