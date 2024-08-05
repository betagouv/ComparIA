function() {
// start_arena_btn code: check for ToS+Waiver

    const acceptWaiverCheckbox = document.getElementById('accept_waiver');

    const acceptTosCheckbox = document.getElementById('accept_tos');

    const startArenaBtn = document.getElementById('start_arena_btn');

    function checkAndEnableButton() {
        const shouldEnable = acceptWaiverCheckbox.checked && acceptTosCheckbox.checked;

        startArenaBtn.disabled = !shouldEnable;
    }

    acceptWaiverCheckbox.addEventListener('change', function() {
        checkAndEnableButton();
    });

    acceptTosCheckbox.addEventListener('change', function() {
        checkAndEnableButton();
    });

    // Initial check
    checkAndEnableButton();
// scroll to guided area if selected    

  const scrollButton = document.getElementById('guided-mode');
  const targetElement = document.getElementById('guided-area');

  // only works on second click :(
  scrollButton.addEventListener('click', () => {
    targetElement.scrollIntoView({ 
      behavior: 'smooth'
    });
  });

  // window.onscroll = function() {
  //   // const headerPlaceholder = document.querySelector('#header-placeholder');
  //   const header = document.querySelector('#header-html');      
  //   const headerBottom = header.offsetTop + header.offsetHeight;
  //   const stepper = document.querySelector('#stepper-html');
  //   // const stepperHeight = stepper.offsetHeight;
  //   if (window.scrollY > headerBottom) {
  //     stepper.classList.add('sticky');
  //     // headerPlaceholder.style.height = header.offsetHeight + stepperHeight;
  //   } else {
  //     stepper.classList.remove('sticky');
  //   }
  //   };

// // scroll to last prompt
//   var left = document.querySelector('#chatbot-0 .user'); 
//   var last_left = left.items(left.length-1);
//   var right = document.querySelector('#chatbot-1 .user'); 
//   var last_right = right.items(right.length-1);
//   const sendButton = document.getElementById('send-btn');
// 
//   // FIXME: only when our prompt is added to chat
//   sendButton.addEventListener('click', () => {
//     last_left.scrollIntoView({ 
//       behavior: 'smooth'
//     });
//     last_right.scrollIntoView({ 
//       behavior: 'smooth'
//     });
//   });

}

