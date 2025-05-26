<div
    class="message pending"
    role="status"
    aria-label="Loading response"
    aria-live="polite"
>
    <span class="sr-only">Loading content</span>
    <div class="disc left"></div>
    <div class="disc right"></div>
</div>

<style>
    .pending {
        display: flex;
        flex-direction: row;
        justify-content: center;
        align-items: center;
        align-self: center;
        gap: 0px; /* You might adjust this gap based on the animation */
        width: 100%;
        position: relative; /* Needed for absolute positioning of discs */
    }

    .disc {
        position: absolute;
        width: 15px; /* Adjust disc size as needed */
        height: 15px; /* Adjust disc size as needed */
        border-radius: 50%;
        top: 50%;
    }

    .disc.left {
        background-color: #ff9575;
        animation: animate-left 1.5s infinite ease-in-out;

        left: 50%; /* Start from center */
    }

    .disc.right {
        background-color: #a96afe;
        animation: animate-right 1.5s infinite ease-in-out;

        left: 50%; /* Start from center */
    }

    @keyframes animate-left {
        0% {
            transform: translateX(
                -10px
            ); /* Initial offset from center, full size */
            z-index: 2; /* Starts on top */
        }
        49.9% {
            z-index: 2; /* Keep high z-index before flip */
        }
        50% {
            /* Move from -15px to +15px (total 30px to the right) */
            transform: translateX(calc(10px));
            z-index: 0; /* Drops behind after passing */
        }
        99.9% {
            z-index: 0; /* Keep low z-index before returning */
        }
        100% {
            transform: translateX(
                -10px
            ); /* Return to original position and size */
            z-index: 2; /* Back on top for next cycle */
        }
    }

    /* --- Animation for the Right Disc (Moves left, then back) --- */
    @keyframes animate-right {
        0% {
            transform: translateX(
                10px
            ); /* Initial offset from center, full size */
            z-index: 1; /* Starts behind */
        }
        49.9% {
            z-index: 1; /* Keep low z-index before flip */
        }
        50% {
            transform: translateX(calc(-10px));
            z-index: 3; /* Jumps to the front after passing */
        }
        99.9% {
            z-index: 3; /* Keep high z-index before returning */
        }
        100% {
            transform: translateX(
                10px
            ); /* Return to original position and size */
            z-index: 1; /* Back behind for next cycle */
        }
    }
</style>
