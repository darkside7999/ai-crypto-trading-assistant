import { useState } from "react";

import Dashboard from "./pages/Dashboard";
import LoginPage from "./pages/LoginPage";

export default function App() {
  const [loggedIn, setLoggedIn] = useState(Boolean(localStorage.getItem("access_token")));

  return loggedIn ? <Dashboard /> : <LoginPage onLogin={() => setLoggedIn(true)} />;
}
