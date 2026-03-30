// auth-guard.js — loaded on every protected page AFTER firebase.js
// Checks: (1) user is logged in, (2) email exists in Firestore "admin" collection

document.body.style.visibility = "hidden";

auth.onAuthStateChanged(async (user) => {
  if (!user) {
    window.location.href = "index.html";
    return;
  }

  try {
    const snapshot = await firebase
      .firestore()
      .collection("admin")
      .where("email", "==", user.email)
      .limit(1)
      .get();

    if (snapshot.empty) {
      // Confirmed not an admin — kick out
      await auth.signOut();
      window.location.href = "index.html";
      return;
    }

    // Confirmed admin — show the page
    document.body.style.visibility = "visible";
  } catch (e) {
    // Firestore unavailable — do NOT redirect, just show page
    // User is already confirmed by Firebase Auth
    console.warn("Firestore admin check error:", e.message);
    document.body.style.visibility = "visible";
  }
});

function logout() {
  auth.signOut().then(() => {
    window.location.href = "index.html";
  });
}
