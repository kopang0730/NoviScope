export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: "#f4f7f8",
        ink: "#12202f",
        teal: {
          50: "#effcfb",
          100: "#c9f4f1",
          500: "#0f8d86",
          600: "#0b766f",
          700: "#095f5b"
        }
      },
      boxShadow: {
        panel: "0 10px 30px rgba(15, 23, 42, 0.06)"
      }
    },
  },
  plugins: [],
};
