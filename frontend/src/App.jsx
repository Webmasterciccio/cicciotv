import { Route, Routes } from 'react-router-dom'
import Nav from './components/Nav.jsx'
import Dashboard from './pages/Dashboard.jsx'
import Search from './pages/Search.jsx'
import SeriesDetail from './pages/SeriesDetail.jsx'

function App() {
  return (
    <>
      <Nav />
      <main className="page">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/cerca" element={<Search />} />
          <Route path="/serie/:id" element={<SeriesDetail />} />
        </Routes>
      </main>
    </>
  )
}

export default App
