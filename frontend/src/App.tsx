import { createBrowserRouter, createRoutesFromElements, Route, RouterProvider } from 'react-router-dom';

import Home from './pages/main/Home';
import MainLayout from './layouts/MainLayout';

function App() {

    const router = createBrowserRouter(
        createRoutesFromElements(
            <>
                <Route path='/' element={<MainLayout />} >
                    <Route index element={<Home />} />
                </Route>
            </>
        )
    );

    return (
        <RouterProvider router={router} />
    )
}

export default App
