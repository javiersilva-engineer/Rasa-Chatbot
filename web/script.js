const API_URL = 'http://localhost:5005/webhooks/rest/webhook';
const chatMessages = document.getElementById('chatMessages');
const messageInput = document.getElementById('messageInput');
const sendBtn = document.getElementById('sendBtn');

// Enviar mensaje al presionar Enter
messageInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

// Enviar mensaje al hacer clic en el botón
sendBtn.addEventListener('click', sendMessage);

async function sendMessage() {
    const text = messageInput.value.trim();
    
    if (!text) return;

    // Mostrar mensaje del usuario
    addMessage(text, 'user');
    messageInput.value = '';
    sendBtn.disabled = true;

    // Mostrar indicador de escritura
    const typingId = showTyping();

    try {
        // Enviar mensaje a Rasa
        const response = await fetch(API_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: text,
                sender: 'web_user'
            })
        });

        if (!response.ok) {
            throw new Error('Error en la conexión con el servidor');
        }

        const data = await response.json();

        // Eliminar indicador de escritura
        removeTyping(typingId);

        // Mostrar respuestas del bot
        if (data.length > 0) {
            data.forEach(msg => {
                if (msg.text) {
                    addMessage(msg.text, 'bot');
                }
                // Agregar soporte para botones
                if (msg.buttons && msg.buttons.length > 0) {
                    addButtons(msg.buttons);
                }
            });
        } else {
            addMessage('No entendí tu mensaje, ¿puedes reformularlo?', 'bot');
        }
    } catch (error) {
        removeTyping(typingId);
        console.error('Error:', error);
        addMessage('❌ Error: No puedo conectar con el servidor. ¿Está corriendo Rasa?', 'error');
    } finally {
        sendBtn.disabled = false;
        messageInput.focus();
    }
}

async function sendButtonPayload(payload) {
    sendBtn.disabled = true;
    const typingId = showTyping();

    try {
        const response = await fetch(API_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: payload,
                sender: 'web_user'
            })
        });

        if (!response.ok) {
            throw new Error('Error en la conexión con el servidor');
        }

        const data = await response.json();
        removeTyping(typingId);

        if (data.length > 0) {
            data.forEach(msg => {
                if (msg.text) {
                    addMessage(msg.text, 'bot');
                }
                if (msg.buttons && msg.buttons.length > 0) {
                    addButtons(msg.buttons);
                }
            });
        } else {
            addMessage('No entendí tu mensaje, ¿puedes reformularlo?', 'bot');
        }
    } catch (error) {
        removeTyping(typingId);
        console.error('Error:', error);
        addMessage('❌ Error: No puedo conectar con el servidor. ¿Está corriendo Rasa?', 'error');
    } finally {
        sendBtn.disabled = false;
        messageInput.focus();
    }
}

function addMessage(text, sender) {
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('message', sender);

    const content = document.createElement('div');
    content.classList.add('message-content');
    
    // Detectar y convertir URLs a enlaces
    content.innerHTML = convertUrlsToLinks(text);

    messageDiv.appendChild(content);
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function convertUrlsToLinks(text) {
    // Expresión regular para detectar URLs
    const urlRegex = /(https?:\/\/[^\s]+)/g;
    
    return text.replace(urlRegex, (url) => {
        return `<a href="${url}" target="_blank" style="color: #E91E63; text-decoration: underline; cursor: pointer;">${url}</a>`;
    });
}

function addButtons(buttons) {
    const buttonContainer = document.createElement('div');
    buttonContainer.classList.add('message', 'bot');
    
    const buttonsDiv = document.createElement('div');
    buttonsDiv.style.cssText = `
        display: flex;
        flex-direction: column;
        gap: 8px;
        max-width: 80%;
        margin-top: 5px;
    `;
    
    buttons.forEach(button => {
        const btn = document.createElement('button');
        btn.textContent = button.title;
        btn.style.cssText = `
            background: #757575ff;
            color: white;
            border: none;
            border-radius: 20px;
            padding: 12px 16px;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.2s;
            text-align: left;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        `;
        
        btn.onmouseover = () => {
            btn.style.transform = 'scale(1.02)';
            btn.style.boxShadow = '0 4px 8px rgba(0,0,0,0.2)';
        };
        
        btn.onmouseout = () => {
            btn.style.transform = 'scale(1)';
            btn.style.boxShadow = 'none';
        };
        
        btn.onclick = () => {
            // Mostrar el mensaje del usuario
            addMessage(button.title, 'user');
            
            // Enviar el payload al servidor
            sendButtonPayload(button.payload);
        };
        
        buttonsDiv.appendChild(btn);
    });
    
    buttonContainer.appendChild(buttonsDiv);
    chatMessages.appendChild(buttonContainer);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function showTyping() {
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('message', 'bot');
    messageDiv.id = 'typing-indicator';

    const typing = document.createElement('div');
    typing.classList.add('typing');
    typing.innerHTML = '<span></span><span></span><span></span>';

    messageDiv.appendChild(typing);
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    return messageDiv.id;
}

function removeTyping(id) {
    const element = document.getElementById(id);
    if (element) {
        element.remove();
    }
}

// Mensaje de bienvenida con botones
window.addEventListener('load', async () => {
    // Mostrar mensaje de bienvenida
    addMessage('¡Hola! Soy Luna. ¿En qué puedo ayudarle hoy?', 'bot');
    
    messageInput.focus();
});
