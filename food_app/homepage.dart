
import 'package:flutter/material.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:cloud_firestore/cloud_firestore.dart'; 
import 'package:foodapp/pages/InspectionHistoryScreen.dart'; 
import 'package:foodapp/pages/blutoothmod.dart';
import 'package:foodapp/pages/settings.dart'; 
import 'reportissue.dart';// Ensure SettingsPage is defined here

class HomePage extends StatelessWidget {
  const HomePage({super.key});

  // Helper to fetch the username from Firestore
  Future<String> _fetchUsername() async {
    final user = FirebaseAuth.instance.currentUser;
    if (user != null) {
      final snap = await FirebaseFirestore.instance
          .collection('users')
          .where('uid', isEqualTo: user.uid)
          .get();
      if (snap.docs.isNotEmpty) {
        return snap.docs.first.id; 
      }
    }
    return "User";
  }

  @override
  Widget build(BuildContext context) {
    // These titles must match the IF statements in onTap exactly
    final List<Map<String, dynamic>> options = [
      {'title': 'View History', 'icon': Icons.history},
      {'title': 'Report Issue', 'icon': Icons.report_problem},
      {'title': 'Settings', 'icon': Icons.settings},
      {'title': 'About', 'icon': Icons.info},
    ];

    return Scaffold(
      appBar: AppBar(
        title: const Text("Home Page"),
        centerTitle: true,
      ),
      drawer: Drawer(
        child: Column(
          children: [
            UserAccountsDrawerHeader(
              currentAccountPicture: const CircleAvatar(
                backgroundColor: Colors.white,
                child: Icon(Icons.person, size: 40, color: Colors.blue),
              ),
              accountName: FutureBuilder<String>(
                future: _fetchUsername(),
                builder: (context, snapshot) {
                  return Text(snapshot.data ?? "Loading...");
                },
              ),
              accountEmail: Text(FirebaseAuth.instance.currentUser?.email ?? "Not logged in"),
            ),
            Expanded(
              child: ListView.builder(
                padding: EdgeInsets.zero,
                itemCount: options.length,
                itemBuilder: (context, index) {
                  final option = options[index];
                  return ListTile(
                    leading: Icon(option['icon'], color: Colors.blue),
                    title: Text(option['title']),
                    onTap: () async {
                      final String title = option['title'];
                      
                      // Close the drawer first
                      Navigator.pop(context);

                      if (title == 'View History') {
                        final username = await _fetchUsername();
                        if (context.mounted) {
                          Navigator.push(
                            context,
                            MaterialPageRoute(
                              builder: (context) => InspectionHistoryScreen(username: username),
                            ),
                          );
                        }
                      } 
                      else if (title == 'Settings') {
                        // This triggers your SettingsPage
                        Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (context) => const SettingsPage(),
                          ),
                        );
                      }
                      else if (title == 'About') {
                        showAboutDialog(
                          context: context,
                          applicationName: 'FoodApp',
                          applicationVersion: '1.0.0',
                          children: [const Text('This is a demo app by Alan.')],
                        );
                      }
                      else if (title == 'Report Issue') {
                         Navigator.push(
                                  context,
                          MaterialPageRoute(builder: (context) => const ReportIssuePage()),
                          );
                        }
                      // Note: 'Report Issue' is currently a placeholder
                    },
                  );
                },
              ),
            ),
            const Divider(),
            ListTile(
              leading: const Icon(Icons.logout, color: Colors.red),
              title: const Text("Logout", style: TextStyle(color: Colors.red, fontWeight: FontWeight.bold)),
              onTap: () async {
                await FirebaseAuth.instance.signOut();
                // If you use named routes for login, add:
                // Navigator.of(context).pushReplacementNamed('/login');
              },
            ),
            const SizedBox(height: 20),
          ],
        ),
      ),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Text(
              "Connect to your device via BLE",
              style: TextStyle(color: Colors.grey),
            ),
            const SizedBox(height: 30),
            ElevatedButton.icon(
              style: ElevatedButton.styleFrom(
                padding: const EdgeInsets.symmetric(horizontal: 30, vertical: 15),
                backgroundColor: Colors.blueAccent,
              ),
              onPressed: () {
                Navigator.push(
                  context,
                  MaterialPageRoute(builder: (context) => const BLEScannerPage()),
                );
              },
              icon: const Icon(Icons.bluetooth, color: Colors.white),
              label: const Text("Pair Device", style: TextStyle(color: Colors.white)),
            ),
          ],
        ),
      ),
    );
  }
}