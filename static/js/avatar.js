document.addEventListener('DOMContentLoaded', function() {
    const avatarCharacterContainer = document.getElementById('avatar-character-container');
    const avatarEmoji = document.getElementById('avatar-character-emoji');
    const chatBox = document.getElementById('avatar-chat-box');
    const closeBtn = document.getElementById('avatar-chat-close');
    const chatInput = document.getElementById('avatar-chat-input');
    const sendBtn = document.getElementById('avatar-chat-send');
    const messagesContainer = document.getElementById('avatar-chat-messages');

    // Toggle chat visibility
    avatarCharacterContainer.addEventListener('click', function() {
        if (chatBox.style.display === 'none' || chatBox.style.display === '') {
            chatBox.style.display = 'flex';
            chatInput.focus();
            if(document.getElementById('feedback-modal')) {
                document.getElementById('feedback-modal').style.display = 'none';
            }
        } else {
            chatBox.style.display = 'none';
        }
    });

    closeBtn.addEventListener('click', function() {
        chatBox.style.display = 'none';
    });

    // Send message functions
    function appendMessage(text, sender) {
        const msgDiv = document.createElement('div');
        msgDiv.classList.add('avatar-message');
        msgDiv.classList.add(sender === 'user' ? 'message-user' : 'message-bot');
        msgDiv.innerHTML = text; // Allow HTML from bot (e.g. <br>)
        messagesContainer.appendChild(msgDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    function removeAnimations() {
        avatarEmoji.classList.remove('animate-wave');
        avatarEmoji.classList.remove('animate-present');
    }

    function handleGesture(gesture) {
        removeAnimations();
        if (gesture === 'wave') {
            avatarEmoji.classList.add('animate-wave');
            // Remove animation after a few seconds
            setTimeout(removeAnimations, 3000);
        } else if (gesture === 'present' || gesture === 'thumbs_up') {
            avatarEmoji.classList.add('animate-present');
            setTimeout(removeAnimations, 2000);
        }
    }

    function sendMessage() {
        const message = chatInput.value.trim();
        if (!message) return;

        appendMessage(message, 'user');
        chatInput.value = '';

        // API call to avatar/chat/
        fetch('/avatar/chat/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ message: message })
        })
        .then(response => response.json())
        .then(data => {
            appendMessage(data.text, 'bot');
            if (data.gesture) {
                handleGesture(data.gesture);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            appendMessage("Sorry, I'm having trouble connecting right now.", 'bot');
        });
    }

    sendBtn.addEventListener('click', sendMessage);

    chatInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });

    // Feedback Logic
    const feedbackBtn = document.getElementById('avatar-feedback-btn');
    const feedbackModal = document.getElementById('feedback-modal');
    const feedbackClose = document.getElementById('feedback-modal-close');
    const feedbackSubmit = document.getElementById('submit-feedback-btn');
    const feedbackTextarea = document.getElementById('feedback-textarea');
    const feedbackMsg = document.getElementById('feedback-message');

    if (feedbackBtn && feedbackModal) {
        feedbackBtn.addEventListener('click', () => {
            if (feedbackModal.style.display === 'none' || feedbackModal.style.display === '') {
                feedbackModal.style.display = 'flex';
                feedbackTextarea.focus();
                feedbackMsg.style.display = 'none';
                feedbackTextarea.value = '';
                chatBox.style.display = 'none'; // Close chat if open
            } else {
                feedbackModal.style.display = 'none';
            }
        });
    }

    if (feedbackClose) {
        feedbackClose.addEventListener('click', () => {
            feedbackModal.style.display = 'none';
        });
    }

    if (feedbackSubmit) {
        feedbackSubmit.addEventListener('click', () => {
            const msg = feedbackTextarea.value.trim();
            if (!msg) return;

            feedbackSubmit.disabled = true;
            feedbackSubmit.innerText = 'Sending...';

            fetch('/accounts/submit-feedback/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message: msg })
            })
            .then(response => response.json())
            .then(data => {
                feedbackSubmit.disabled = false;
                feedbackSubmit.innerText = 'Submit';
                
                if (data.success) {
                    feedbackMsg.style.color = 'green';
                    feedbackMsg.innerText = 'Feedback sent successfully! Thank you.';
                    feedbackMsg.style.display = 'block';
                    feedbackTextarea.value = '';
                    setTimeout(() => {
                        feedbackModal.style.display = 'none';
                    }, 2500);
                } else {
                    feedbackMsg.style.color = 'red';
                    feedbackMsg.innerText = data.error || 'Failed to send feedback.';
                    feedbackMsg.style.display = 'block';
                }
            })
            .catch(error => {
                feedbackSubmit.disabled = false;
                feedbackSubmit.innerText = 'Submit';
                feedbackMsg.style.color = 'red';
                feedbackMsg.innerText = 'An error occurred. Please try again.';
                feedbackMsg.style.display = 'block';
                console.error('Feedback Error:', error);
            });
        });
    }
});
