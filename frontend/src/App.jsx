import { Route, Routes } from 'react-router-dom'
import Nav from './components/Nav.jsx'
import Dashboard from './pages/Dashboard.jsx'
import Search from './pages/Search.jsx'
import SeriesDetail from './pages/SeriesDetail.jsx'
import Stats from './pages/Stats.jsx'
import Settings from './pages/Settings.jsx'

function App() {
  return (
    <>
      <Nav />
      <main className="page">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/cerca" element={<Search />} />
          <Route path="/serie/:id" element={<SeriesDetail />} />
          <Route path="/statistiche" element={<Stats />} />
          <Route path="/impostazioni" element={<Settings />} />
        </Routes>
      </main>
    </>
  )
}

export default App
