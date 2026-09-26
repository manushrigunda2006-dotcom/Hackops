import { Routes, Route } from "react-router-dom";
import Navbar from "./components/Navbar";
import Gallery from "./pages/Gallery";
import ProjectDetail from "./pages/ProjectDetail";
import Login from "./pages/Login";
import SubmitProject from "./pages/SubmitProject";
import TeamJoin from "./pages/TeamJoin";
import CreateEvent from "./pages/CreateEvent";
import NotFound from "./pages/NotFound";

export default function App() {
  return (
    <>
      <Navbar />
      <Routes>
        <Route path="/" element={<Gallery />} />
        <Route path="/projects/:id" element={<ProjectDetail />} />
        <Route path="/submit" element={<SubmitProject />} />
        <Route path="/teams/join" element={<TeamJoin />} />
        <Route path="/teams/join/:token" element={<TeamJoin />} />
        <Route path="/events/new" element={<CreateEvent />} />
        <Route path="/login" element={<Login />} />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </>
  );
}
