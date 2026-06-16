# Care Companion 🏥

> A Production-Grade, AI-Powered Over-the-Counter (OTC) Medication Recommendation & Symptom Checking Platform.

Care Companion is a full-stack web application designed to help users identify symptoms and explore safe, relevant over-the-counter (OTC) medication options. Leveraging an **AI-powered chatbot** and **real-time OpenFDA API integration**, it provides personalized suggestions, detailed drug usage, dosage instructions, and critical safety disclaimers.

---

## 🚀 Key Features

* **Symptom Checker Form**: Guided questionnaire allowing users to input primary and secondary symptoms, along with duration, to receive immediate guidance.
* **AI Chat Assistant**: Dynamic chatbot (powered by LLMs like GPT-4o-mini or Gemini) that explains potential causes, recommends OTC remedies, and provides safety warnings.
* **Live OTC Medication Search**: Seamless integration with the **OpenFDA API** to search for OTC drugs by brand name, generic name, or active ingredients.
* **Curated Local Fallback DB**: Resilient offline database matching common symptoms (cough, fever, headache, allergy, heartburn, sore throat) to proven medications when the FDA API is unreachable.
* **Safety & Disclaimers**: Integrated warning boundaries, custom disclaimer prompts, and structured indicators to ensure users consult medical professionals first.
* **User Authentication**: Secure JWT-based registration, login, and profile management systems backed by MongoDB.
* **Premium Glassmorphic Design**: Modern CSS styling with smooth transitions, customized overlays, and a responsive responsive layout.

---

## 📂 Project Structure

```
Care-Companion/
├── backend/                  # Flask Python Server
│   ├── auth.py               # JWT and Bcrypt Authentication logic
│   ├── seed.py               # MongoDB mock data seeding
│   ├── server.py             # Main entry point & Flask Application
│   ├── routes_v3.py          # Primary application routes (OpenFDA search & LLM chatbot)
│   ├── v2_routes.py          # Legacy routes scaffold
│   └── requirements.txt      # Python dependencies
├── src/                      # Vite + React Frontend
│   ├── components/
│   │   ├── chat/             # MessageBubble, ChatInterface, ChatInput components
│   │   └── common/           # Header, Footer navigation elements
│   ├── context/              # React AuthContext and ChatContext providers
│   ├── pages/                # Home, Chat, Medications, Profile, About pages
│   ├── styles/               # Glassmorphic globals & styled layouts
│   ├── App.jsx               # Application routing table
│   └── Main.jsx              # React mounting logic
├── package.json              # Frontend npm packaging configuration
├── vite.config.js            # Vite build setup
└── Index.html                # Single Page App wrapper
```

---

## 🛠️ Installation & Setup

### Prerequisites
- **Node.js** (v16+) & **npm**
- **Python** (v3.9+) & `pip`
- **MongoDB** (running locally or a connection string)

### 1. Backend Setup
1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```
4. Create a `.env` file in the `backend/` directory:
   ```env
   PORT=5000
   MONGO_URL=mongodb://localhost:27017
   DB_NAME=gofarmwork
   JWT_SECRET=your_jwt_secret_here
   OPENAI_API_KEY=your_openai_api_key_here
   ```
5. Seed the database (optional) and run the Flask server:
   ```bash
   python server.py
   ```
   The backend will start running on `http://localhost:5000`.

### 2. Frontend Setup
1. From the root directory, install the dependencies:
   ```bash
   npm install
   ```
2. Start the Vite development server:
   ```bash
   npm run dev
   ```
   The application will be accessible at `http://localhost:5173`.

---

## 🛡️ Medical Safety Disclaimer
Care Companion uses artificial intelligence and public medical datasets (OpenFDA) to provide educational and informational material regarding over-the-counter medications. It **does not** provide medical advice, diagnosis, or treatment. Users must always read physical drug labels, verify dosages, and consult a qualified healthcare professional before starting any new medication.

---

## 📄 License
This project is licensed under the MIT License.
