import { NavLink } from 'react-router-dom'

function Nav() {
  return (
    <header className="nav">
      <NavLink to="/" className="brand">
        CiccioTV
      </NavLink>
      <nav>
        <NavLink to="/" end className={({ isActive }) => (isActive ? 'active' : '')}>
          Libreria
        </NavLink>
        <NavLink to="/cerca" className={({ isActive }) => (isActive ? 'active' : '')}>
          Cerca
        </NavLink>
      </nav>
    </header>
  )
}

export default Nav
