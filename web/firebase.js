// ── Firebase Compat SDK (loaded via CDN scripts in each HTML file) ──
const firebaseConfig = {
  apiKey: "AIzaSyBZgPMBhlgqjp0IQlpRir1PJnk4RrcME84",
  authDomain: "foodapp-401b2.firebaseapp.com",
  databaseURL:
    "https://foodapp-401b2-default-rtdb.asia-southeast1.firebasedatabase.app",
  projectId: "foodapp-401b2",
  storageBucket: "foodapp-401b2.firebasestorage.app",
  messagingSenderId: "138750698992",
  appId: "1:138750698992:web:8b61b62112a13833296935",
  measurementId: "G-56VJYVE0HE",
};

firebase.initializeApp(firebaseConfig);

const auth = firebase.auth();
const db = firebase.database(); // Realtime DB — used by auth-guard + feedback
const fs = firebase.firestore(); // Firestore   — used by reports
