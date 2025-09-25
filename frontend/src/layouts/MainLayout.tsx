import { Outlet } from 'react-router-dom';
import Navbar from '../components/layouts/Navbar';

const MainLayout = () => {
    return (
        <div className="relative min-h-screen">
            <Navbar />
            <Outlet />
        </div>
    );
}

export default MainLayout;