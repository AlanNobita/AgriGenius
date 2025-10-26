const chatsContainer = document.querySelector(".chats-container")
const Container = document.querySelector(".chat-container")
const promptForm = document.querySelector(".prompt-form");
const promptInput = promptForm.querySelector(".prompt-input");
const fileInput = promptForm.querySelector("#file-input");
const fileUploadWrapper = promptForm.querySelector(".file-upload-wrapper");

// This file is deprecated - chat functionality moved to chat.html
// API calls now go through Flask backend for security

let userMessage = "";
const chatHistory = [];

// Function to create message elements
const createMsgElement = (content, ...classes) => {
  const div = document.createElement("div");
  div.classList.add("message", ...classes);
  div.innerHTML =content;
  return div;
}

// Scroll to the bottom of the container
const scrollToBottom = () => Container.scrollTo({ top: Container.scrollHeight, behavior: "smooth"});

// Simulate typing effect for bot response
const typingEffect = (text, textElement, botMsgDiv) => {
  textElement.textContent = "";
  const words = text.split(" ");
  let wordIndex = 0;

  // Set an interval to type each word
  const typingInterval = setInterval(() => {
    if(wordIndex < words.length) {
      textElement.textContent += (wordIndex === 0 ? "" : " ") + words[wordIndex++];
      botMsgDiv.classList.remove("loading");
      scrollToBottom()
    } else {
      botMsgDiv.classList.remove("loading");
    } 
  }, 40);
}

// Make the API call bot response
const generateResponse= async (botMsgDiv) => {
  const textElement = botMsgDiv.querySelector(".message-text")

  // Add user message to the chat history
  chatHistory.push({
    role: "user",
    parts: [{ text: userMessage}]
  });

  try {
    // Send the chat history to the API to get a response
    const response = await fetch(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ contents: chatHistory})
    });

    const data = await response.json();
    if(!response.ok) throw new Error(data.error.message);

    // Process the response text and display with typing effect
    const responseText = data.candidates[0].content.parts[0].text.replace(/\*\*([^*]+)\*\*/g, "$1").trim();
    textElement.textContent = responseText;
    typingEffect(responseText, textElement, botMsgDiv);
    chatHistory.push({role: "model", parts:[{text: responseText}]});

   } catch (error) {
    console.log(error)
  }
}

// handle the form submission
const handleFormSubmit = (e) => {
  e.preventDefault();
  userMessage = promptInput.value.trim();

  if(!userMessage) return;

  promptInput.value = "";

  // Generate user message HTML and add in the chat container
  const userMsgHTML = '<p class="message-text"></p>';
  const userMsgDiv = createMsgElement(userMsgHTML, "user-message");

  userMsgDiv.querySelector(".message-text").textContent = userMessage;
  chatsContainer.appendChild(userMsgDiv);
  scrollToBottom();

  setTimeout(() => {
    //Generate bot message HTML and in the chats container in 600ms
    const botMsgHTML = '<img src="home/alan/documents/codes/farmgenius_website/images/gemini-chatbot-logo.svg" class="avater"><p class="message-text">Just a sec..</p>';
    const botMsgDiv = createMsgElement(botMsgHTML, "bot-message", "loading");
    chatsContainer.appendChild(botMsgDiv);
    scrollToBottom();
    generateResponse(botMsgDiv);
  }, 600);

}

// Handle file input change (File upload)
fileInput,addEventListener("change", () => {
  const file = fileInput.files[0];
  if(!file) return;

  const isImage = file.type.startsWith("image/");
  const reader = new FileReader();
  reader.readAsDataURL(file);

  reader.onload = (e) => {
   fileInput.value = "";
    fileUploadWrapper.querySelector(".file-previw").src = e.target.result;
    fileUploadWrapper.classList.add("active", isImage ? "img-attached" : "file-attached");
  }
});

promptForm.addEventListener("submit", handleFormSubmit);
promptForm.querySelector("#add-file-btn").addEventListener("click", () => fileInput.click());