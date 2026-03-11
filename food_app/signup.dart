/*import 'package:flutter/material.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:cloud_firestore/cloud_firestore.dart';

class SignUpPage extends StatefulWidget {
  const SignUpPage({super.key});
  @override
  State<SignUpPage> createState() => _SignUpPageState();
}

class _SignUpPageState extends State<SignUpPage> {
  final _nameController = TextEditingController();
  final _usernameController = TextEditingController();
  final _phoneController = TextEditingController();
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _isLoading = false;

  Future<void> signUp() async {
    final name = _nameController.text.trim();
    final username = _usernameController.text.trim().toLowerCase();
    final email = _emailController.text.trim();
    final password = _passwordController.text.trim();
    final phone = _phoneController.text.trim();

    if (name.isEmpty || username.isEmpty || email.isEmpty || password.isEmpty) {
      _showMessage("Please fill in all fields.", isError: true);
      return;
    }

    setState(() => _isLoading = true);

    User? user;

    try {
      // 1. Create Auth Account
      UserCredential userCredential = await FirebaseAuth.instance
          .createUserWithEmailAndPassword(email: email, password: password);
      
      user = userCredential.user;

      // 2. Save Data to Firestore
      await FirebaseFirestore.instance
          .collection('users')
          .doc(user!.uid)
          .set({
        'full_name': name,
        'username': username,
        'phone': phone,
        'email': email,
        'uid': user.uid,
        'createdAt': FieldValue.serverTimestamp(),
      });

      // 3. SUCCESS! Show Message
      if (mounted) {
        _showMessage("Account created successfully! Welcome, $name 🎉", isError: false);
      }

      // Note: We don't need Navigator.pop/push because StreamBuilder in main.dart 
      // will see FirebaseAuth.instance.currentUser is now not null and 
      // automatically show the HomePage.

    } on FirebaseAuthException catch (e) {
      if (mounted) _showMessage(e.message ?? "Registration failed", isError: true);
    } catch (e) {
      // Cleanup if Firestore fails
      if (user != null) {
        await user.delete(); 
        await FirebaseAuth.instance.signOut();
      }
      if (mounted) _showMessage("Database Error: Check your internet.", isError: true);
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  // Helper to show both Error and Success messages
  void _showMessage(String m, {required bool isError}) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(m), 
        backgroundColor: isError ? Colors.redAccent : Colors.green,
        duration: const Duration(seconds: 3),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Create Account")),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(25),
        child: Column(
          children: [
            _box(_nameController, "Full Name", Icons.person),
            const SizedBox(height: 15),
            _box(_usernameController, "User ID", Icons.alternate_email),
            const SizedBox(height: 15),
            _box(_phoneController, "Phone", Icons.phone, type: TextInputType.phone),
            const SizedBox(height: 15),
            _box(_emailController, "Email", Icons.email, type: TextInputType.emailAddress),
            const SizedBox(height: 15),
            _box(_passwordController, "Password", Icons.lock, isPass: true),
            const SizedBox(height: 30),
            _isLoading 
              ? const CircularProgressIndicator()
              : SizedBox(
                  width: double.infinity,
                  height: 55,
                  child: ElevatedButton(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.blueAccent,
                      foregroundColor: Colors.white,
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12))
                    ),
                    onPressed: signUp, 
                    child: const Text("Register", style: TextStyle(fontSize: 18)),
                  ),
                ),
          ],
        ),
      ),
    );
  }

  Widget _box(TextEditingController c, String l, IconData i, {bool isPass = false, TextInputType type = TextInputType.text}) {
    return TextField(
      controller: c,
      obscureText: isPass,
      keyboardType: type,
      decoration: InputDecoration(
        labelText: l, 
        prefixIcon: Icon(i), 
        border: const OutlineInputBorder(borderRadius: BorderRadius.all(Radius.circular(12)))
      ),
    );
  }
}*/
import 'package:flutter/material.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:cloud_firestore/cloud_firestore.dart';

class SignUpPage extends StatefulWidget {
  const SignUpPage({super.key});
  @override
  State<SignUpPage> createState() => _SignUpPageState();
}

class _SignUpPageState extends State<SignUpPage> {
  final _nameController = TextEditingController();
  final _usernameController = TextEditingController();
  final _phoneController = TextEditingController();
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _isLoading = false;

  Future<void> signUp() async {
    final name = _nameController.text.trim();
    final username = _usernameController.text.trim().toLowerCase(); // User ID from UI
    final email = _emailController.text.trim();
    final password = _passwordController.text.trim();
    final phone = _phoneController.text.trim();

    if (name.isEmpty || username.isEmpty || email.isEmpty || password.isEmpty) {
      _showMessage("Please fill in all fields.", isError: true);
      return;
    }

    setState(() => _isLoading = true);

    User? user;

    try {
      // 1. Check if the Document ID (User ID/Username) already exists
      final userDoc = await FirebaseFirestore.instance
          .collection('users')
          .doc(username)
          .get();

      if (userDoc.exists) {
        _showMessage("This User ID is already taken. Try another.", isError: true);
        setState(() => _isLoading = false);
        return;
      }

      // 2. Create Auth Account
      UserCredential userCredential = await FirebaseAuth.instance
          .createUserWithEmailAndPassword(email: email, password: password);
      
      user = userCredential.user;

      // 3. Save Data to Firestore using 'username' as the Document ID
      await FirebaseFirestore.instance
          .collection('users')
          .doc(username) // <--- Set document ID to the User ID provided
          .set({
        'full_name': name,
        'username': username,
        'phone': phone,
        'email': email,
        'uid': user!.uid, // Store the Auth UID as a field for security rules
        'createdAt': FieldValue.serverTimestamp(),
      });

      // 4. SUCCESS!
      if (mounted) {
        _showMessage("Account created successfully! Welcome, $name 🎉", isError: false);
      }

    } on FirebaseAuthException catch (e) {
      if (mounted) _showMessage(e.message ?? "Registration failed", isError: true);
    } catch (e) {
      // Cleanup: If Firestore fails, delete the Auth user so they can try again
      if (user != null) {
        await user.delete(); 
        await FirebaseAuth.instance.signOut();
      }
      if (mounted) _showMessage("Database Error: Check your internet.", isError: true);
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  // Helper to show both Error and Success messages
  void _showMessage(String m, {required bool isError}) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(m), 
        backgroundColor: isError ? Colors.redAccent : Colors.green,
        duration: const Duration(seconds: 3),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Create Account")),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(25),
        child: Column(
          children: [
            _box(_nameController, "Full Name", Icons.person),
            const SizedBox(height: 15),
            _box(_usernameController, "User ID", Icons.alternate_email),
            const SizedBox(height: 15),
            _box(_phoneController, "Phone", Icons.phone, type: TextInputType.phone),
            const SizedBox(height: 15),
            _box(_emailController, "Email", Icons.email, type: TextInputType.emailAddress),
            const SizedBox(height: 15),
            _box(_passwordController, "Password", Icons.lock, isPass: true),
            const SizedBox(height: 30),
            _isLoading 
              ? const CircularProgressIndicator()
              : SizedBox(
                  width: double.infinity,
                  height: 55,
                  child: ElevatedButton(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.blueAccent,
                      foregroundColor: Colors.white,
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12))
                    ),
                    onPressed: signUp, 
                    child: const Text("Register", style: TextStyle(fontSize: 18)),
                  ),
                ),
          ],
        ),
      ),
    );
  }

  Widget _box(TextEditingController c, String l, IconData i, {bool isPass = false, TextInputType type = TextInputType.text}) {
    return TextField(
      controller: c,
      obscureText: isPass,
      keyboardType: type,
      decoration: InputDecoration(
        labelText: l, 
        prefixIcon: Icon(i), 
        border: const OutlineInputBorder(borderRadius: BorderRadius.all(Radius.circular(12)))
      ),
    );
  }
}