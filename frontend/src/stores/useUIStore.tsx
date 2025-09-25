import { create } from "zustand";

type UIState = {
    loading: boolean;

    setLoading: (loading: boolean) => void;
    resetUI: () => void;
};

const useUIStore = create<UIState>((set) => ({
    loading: false,

    setLoading: (loading) => set({ loading }),
    resetUI: () => set({ loading: false }),
}));

export default useUIStore;
