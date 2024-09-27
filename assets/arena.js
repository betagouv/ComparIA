function() {
        

    function adjustFooter() {
      const footer = document.getElementById('send-area');
      const modeScreen = document.getElementById('mode-screen');
      const chatArea = document.getElementById('chat-area');
    
      const footerHeight = footer.offsetHeight;
      // Add bottom padding to the chatArea equal to footer height so it's not hidden
      chatArea.style.paddingBottom = `${footerHeight}px`;
      modeScreen.style.paddingBottom = `${footerHeight}px`;
    }
    window.addEventListener('load', adjustFooter);
    window.addEventListener('resize', adjustFooter);
    window.addEventListener('click', adjustFooter);
    adjustFooter();

}

