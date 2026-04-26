from flask import Flask, request, jsonify
from openai import OpenAI
from flask_cors import CORS
from datetime import datetime
import os
import base64
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# Загружаем токен из .env файла
load_dotenv()

app = Flask(__name__)
CORS(app)

# Токен из переменных окружения
token = os.getenv('GITHUB_TOKEN')
endpoint = "https://models.inference.ai.azure.com"
model_name = "gpt-4o"

client = OpenAI(base_url=endpoint, api_key=token)

# Создаем папки для файлов
UPLOAD_FOLDER = 'uploads'
LOG_FOLDER = 'user_logs'

for folder in [UPLOAD_FOLDER, LOG_FOLDER]:
    if not os.path.exists(folder):
        os.makedirs(folder)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# История диалогов
conversations = {}

def save_user_log(session_id, user_message, image_names=None):
    """Сохраняет логи пользователей"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    photo_info = f" [ФОТО: {image_names}]" if image_names else ""
    
    log_file = os.path.join(LOG_FOLDER, "all_messages.txt")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {session_id[:20]}... | {user_message}{photo_info}\n")
    
    print(f"[{timestamp}] {user_message}{photo_info}")

# HTML код чата
HTML_CODE = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes">
    <title>🤖 AI Чат с фото</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 10px;
        }
        
        .chat-container {
            max-width: 800px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            height: 95vh;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        
        .chat-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px;
            text-align: center;
        }
        
        .chat-header h1 {
            font-size: 20px;
        }
        
        .chat-header p {
            font-size: 12px;
            opacity: 0.9;
            margin-top: 5px;
        }
        
        .chat-messages {
            flex: 1;
            overflow-y: auto;
            padding: 15px;
            background: #f5f5f5;
        }
        
        .message {
            margin-bottom: 15px;
            display: flex;
            animation: fadeIn 0.3s ease-in;
        }
        
        @keyframes fadeIn {
            from {
                opacity: 0;
                transform: translateY(10px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        .message.user {
            justify-content: flex-end;
        }
        
        .message-content {
            max-width: 70%;
            padding: 10px 15px;
            border-radius: 18px;
            word-wrap: break-word;
            font-size: 14px;
        }
        
        .user .message-content {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        
        .bot .message-content {
            background: white;
            color: #333;
            border: 1px solid #e0e0e0;
        }
        
        .message-content img {
            max-width: 200px;
            max-height: 200px;
            border-radius: 10px;
            margin-bottom: 8px;
            cursor: pointer;
        }
        
        .message-avatar {
            width: 30px;
            height: 30px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 8px;
            font-size: 14px;
        }
        
        .bot .message-avatar {
            background: #764ba2;
            color: white;
        }
        
        .user .message-avatar {
            background: #667eea;
            color: white;
        }
        
        .chat-input-container {
            padding: 15px;
            background: white;
            border-top: 1px solid #e0e0e0;
        }
        
        .image-preview-area {
            display: flex;
            gap: 10px;
            margin-bottom: 10px;
            flex-wrap: wrap;
        }
        
        .image-preview {
            position: relative;
            display: inline-block;
        }
        
        .preview-img {
            height: 80px;
            border-radius: 8px;
        }
        
        .remove-image {
            position: absolute;
            top: -8px;
            right: -8px;
            background: red;
            color: white;
            border-radius: 50%;
            width: 22px;
            height: 22px;
            cursor: pointer;
            text-align: center;
            line-height: 20px;
            font-size: 14px;
            font-weight: bold;
        }
        
        .input-controls {
            display: flex;
            gap: 8px;
        }
        
        .chat-input {
            flex: 1;
            padding: 10px;
            border: 2px solid #e0e0e0;
            border-radius: 25px;
            font-size: 14px;
            outline: none;
            resize: none;
            font-family: inherit;
        }
        
        .chat-input:focus {
            border-color: #764ba2;
        }
        
        .send-button,
        .image-button {
            padding: 10px 20px;
            border: none;
            border-radius: 25px;
            font-size: 14px;
            cursor: pointer;
            font-weight: bold;
        }
        
        .send-button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        
        .image-button {
            background: #4CAF50;
            color: white;
        }
        
        .send-button:disabled,
        .image-button:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }
        
        .typing-indicator {
            display: flex;
            gap: 5px;
            padding: 10px 15px;
            background: white;
            border-radius: 18px;
            width: fit-content;
        }
        
        .typing-indicator span {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #999;
            animation: typing 1.4s infinite;
        }
        
        .typing-indicator span:nth-child(2) {
            animation-delay: 0.2s;
        }
        
        .typing-indicator span:nth-child(3) {
            animation-delay: 0.4s;
        }
        
        @keyframes typing {
            0%,
            60%,
            100% {
                transform: translateY(0);
            }
            30% {
                transform: translateY(-10px);
            }
        }
        
        .clear-button {
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: #f44336;
            color: white;
            border: none;
            border-radius: 50px;
            padding: 8px 16px;
            cursor: pointer;
            font-size: 12px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
            z-index: 1000;
        }
        
        @media (max-width: 600px) {
            .message-content {
                max-width: 85%;
                font-size: 13px;
            }
            
            .chat-header h1 {
                font-size: 16px;
            }
            
            .send-button,
            .image-button {
                padding: 8px 16px;
            }
        }
    </style>
</head>
<body>
    <div class="chat-container">
        <div class="chat-header">
            <h1>🤖 GPT-4o Чат с фото</h1>
            <p>Могу описать любое фото! 📸</p>
        </div>
        
        <div class="chat-messages" id="chatMessages">
            <div class="message bot">
                <div class="message-avatar">🤖</div>
                <div class="message-content">Привет! Отправь мне фото, и я опишу что на нём! 😊📸</div>
            </div>
        </div>
        
        <div class="chat-input-container">
            <div class="image-preview-area" id="imagePreviewArea"></div>
            <div class="input-controls">
                <textarea class="chat-input" id="messageInput" placeholder="Напишите вопрос о фото..." rows="2"></textarea>
                <button class="image-button" id="imageButton">📷 Фото</button>
                <button class="send-button" id="sendButton">📤</button>
            </div>
        </div>
    </div>
    <button class="clear-button" id="clearButton">🗑 Очистить</button>
    
    <input type="file" id="fileInput" accept="image/*" multiple style="display: none;">
    
    <script>
        let sessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        let isTyping = false;
        let images = [];
        
        const chatMessages = document.getElementById('chatMessages');
        const messageInput = document.getElementById('messageInput');
        const sendButton = document.getElementById('sendButton');
        const clearButton = document.getElementById('clearButton');
        const imageButton = document.getElementById('imageButton');
        const fileInput = document.getElementById('fileInput');
        const imagePreviewArea = document.getElementById('imagePreviewArea');
        
        function addMessage(text, isUser, imageDataArray = null) {
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${isUser ? 'user' : 'bot'}`;
            
            let content = `<div class="message-avatar">${isUser ? '👤' : '🤖'}</div>`;
            content += `<div class="message-content">`;
            
            if (imageDataArray && imageDataArray.length > 0) {
                for (let imgData of imageDataArray) {
                    content += `<img src="${imgData}" onclick="window.open(this.src)"><br>`;
                }
            }
            
            content += `${escapeHtml(text)}</div>`;
            messageDiv.innerHTML = content;
            chatMessages.appendChild(messageDiv);
            scrollToBottom();
        }
        
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        function scrollToBottom() {
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
        
        function showTyping() {
            if (isTyping) return;
            isTyping = true;
            
            const typingDiv = document.createElement('div');
            typingDiv.className = 'message bot';
            typingDiv.id = 'typingIndicator';
            typingDiv.innerHTML = `
                    <div class="message-avatar">🤖</div>
                    <div class="typing-indicator">
                        <span></span>
                        <span></span>
                        <span></span>
                    </div>
                `;
            chatMessages.appendChild(typingDiv);
            scrollToBottom();
        }
        
        function hideTyping() {
            const indicator = document.getElementById('typingIndicator');
            if (indicator) indicator.remove();
            isTyping = false;
        }
        
        function updateImagePreview() {
            imagePreviewArea.innerHTML = '';
            for (let i = 0; i < images.length; i++) {
                const previewDiv = document.createElement('div');
                previewDiv.className = 'image-preview';
                previewDiv.innerHTML = `
                        <img src="${images[i]}" class="preview-img">
                        <div class="remove-image" onclick="removeImage(${i})">×</div>
                    `;
                imagePreviewArea.appendChild(previewDiv);
            }
        }
        
        function removeImage(index) {
            images.splice(index, 1);
            updateImagePreview();
        }
        
        async function sendMessage() {
            const message = messageInput.value.trim();
            if (!message && images.length === 0) return;
            
            if (images.length > 0) {
                addMessage(message || "Посмотрите на это фото", true, images);
            } else {
                addMessage(message, true);
            }
            
            messageInput.value = '';
            sendButton.disabled = true;
            showTyping();
            
            const formData = new FormData();
            formData.append('message', message);
            formData.append('session_id', sessionId);
            
            for (let i = 0; i < images.length; i++) {
                const response = await fetch(images[i]);
                const blob = await response.blob();
                formData.append('images', blob, `photo_${i}.jpg`);
            }
            
            try {
                const response = await fetch('/chat_with_photos', {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                hideTyping();
                
                if (data.error) {
                    addMessage('❌ ' + data.error, false);
                } else {
                    addMessage(data.reply, false);
                }
            } catch (error) {
                hideTyping();
                addMessage('❌ Ошибка соединения', false);
            } finally {
                sendButton.disabled = false;
                images = [];
                updateImagePreview();
                messageInput.focus();
            }
        }
        
        function clearChat() {
            chatMessages.innerHTML = '';
            addMessage('Привет! Отправь мне фото, и я опишу что на нём! 😊📸', false);
            sessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
            images = [];
            updateImagePreview();
        }
        
        imageButton.addEventListener('click', () => {
            fileInput.click();
        });
        
        fileInput.addEventListener('change', (e) => {
            const files = Array.from(e.target.files);
            for (let file of files) {
                if (file.type.startsWith('image/')) {
                    const reader = new FileReader();
                    reader.onload = function(ev) {
                        images.push(ev.target.result);
                        updateImagePreview();
                    };
                    reader.readAsDataURL(file);
                }
            }
            fileInput.value = '';
        });
        
        messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
        
        sendButton.addEventListener('click', sendMessage);
        clearButton.addEventListener('click', clearChat);
        
        messageInput.focus();
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return HTML_CODE

@app.route('/chat_with_photos', methods=['POST'])
def chat_with_photos():
    try:
        session_id = request.form.get('session_id', 'default')
        user_message = request.form.get('message', '')
        images = request.files.getlist('images')
        
        # Сохраняем логи
        image_names = [img.filename for img in images if img.filename]
        save_user_log(session_id, user_message or "Фото", ', '.join(image_names) if image_names else None)
        
        # Создаем историю
        if session_id not in conversations:
            conversations[session_id] = [
                {"role": "system", "content": "Ты крутой и полезный ассистент. Отвечай всегда на русском языке. Будь дружелюбным и детальным."}
            ]
        
        # Формируем сообщение с фото
        message_content = []
        
        for img in images:
            if img and img.filename:
                img_data = base64.b64encode(img.read()).decode('utf-8')
                file_ext = img.filename.rsplit('.', 1)[1].lower()
                mime_type = f"image/{file_ext}"
                if file_ext == 'jpg':
                    mime_type = 'image/jpeg'
                
                message_content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{mime_type};base64,{img_data}"
                    }
                })
        
        # Добавляем текст
        if user_message:
            message_content.append({"type": "text", "text": user_message})
        else:
            message_content.append({"type": "text", "text": "Опиши подробно что на этом фото"})
        
        # Сохраняем в историю
        conversations[session_id].append({
            "role": "user",
            "content": message_content
        })
        
        # Отправляем запрос к GPT
        response = client.chat.completions.create(
            messages=conversations[session_id],
            model=model_name,
            max_tokens=1000
        )
        
        bot_reply = response.choices[0].message.content
        conversations[session_id].append({"role": "assistant", "content": bot_reply})
        
        return jsonify({"reply": bot_reply})
        
    except Exception as e:
        error_msg = str(e)
        print(f"Ошибка: {error_msg}")
        
        if 'content_policy_violation' in error_msg:
            return jsonify({"error": "Фото не прошло проверку. Попробуйте другое фото (природа, животные, предметы)."}), 200
        else:
            return jsonify({"error": f"Ошибка: {error_msg[:100]}"}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)