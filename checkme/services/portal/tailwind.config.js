/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                primary: {
                    DEFAULT: '#10B981',
                    dark: '#059669',
                    light: '#34D399',
                },
                accent: {
                    DEFAULT: '#F59E0B',
                    dark: '#D97706',
                },
                danger: '#EF4444',
                background: {
                    DEFAULT: '#111827',
                    card: '#1F2937',
                    hover: '#374151',
                },
                border: '#374151',
            },
            fontFamily: {
                sans: ['Inter', 'system-ui', 'sans-serif'],
            },
        },
    },
    plugins: [],
}
