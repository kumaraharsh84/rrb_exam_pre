(function() {
  const theme = localStorage.getItem("rrb_theme") || "light";
  const useDark = theme === "dark";
  
  if (useDark) {
    document.documentElement.classList.add("dark");
  } else {
    document.documentElement.classList.remove("dark");
  }
  
  const observer = new MutationObserver((mutations, obs) => {
    if (document.body) {
      if (useDark) {
        document.body.classList.add("dark-mode");
      } else {
        document.body.classList.remove("dark-mode");
      }
      obs.disconnect();
    }
  });
  
  observer.observe(document.documentElement, {
    childList: true,
    subtree: true
  });
})();
