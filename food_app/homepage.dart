/*import 'package:flutter/material.dart';
import 'package:firebase_auth/firebase_auth.dart';
//import 'package:foodapp/pages/BluetoothPage.dart';
import 'package:foodapp/firebase_options.dart';
import 'package:foodapp/pages/BLEScannerPage.dart';

class HomePage extends StatelessWidget {
  const HomePage({super.key});

  @override
  Widget build(BuildContext context) {
    final List<Map<String, dynamic>> options = [
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
              accountName: const Text("User Profile"),
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
                    onTap: () {
                      Navigator.pop(context); 
                      if (option['title'] == 'About') {
                        showAboutDialog(
                          context: context,
                          applicationName: 'FoodApp',
                          applicationVersion: '1.0.0',
                          children: [const Text('This is a demo app by Alan.')],
                        );
                      }
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
            // 🔹 2. Updated Button to redirect to Bluetooth Page
            ElevatedButton.icon(
              style: ElevatedButton.styleFrom(
                padding: const EdgeInsets.symmetric(horizontal: 30, vertical: 15),
                backgroundColor: Colors.blueAccent,
              ),
              onPressed: () {
                Navigator.push(
                  context,
                  MaterialPageRoute(builder: (context) =>  BLEScannerPage()),
                );
              },
              icon: const Icon(Icons.bluetooth, color: Colors.white), // Change icon to Bluetooth
              label: const Text("Pair Device", style: TextStyle(color: Colors.white)),
            ),
          ],
        ),
      ),
    );
  }
}*/

/*
woking code for home page
import 'package:flutter/material.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:cloud_firestore/cloud_firestore.dart'; 
import 'package:foodapp/pages/BLEScannerPage.dart';
import 'package:foodapp/pages/InspectionHistoryScreen.dart'; // Make sure this file exists

class HomePage extends StatelessWidget {
  const HomePage({super.key});

  // Helper to fetch the username (which acts as our unique Document ID)
  Future<String> _fetchUsername() async {
    final user = FirebaseAuth.instance.currentUser;
    if (user != null) {
      final snap = await FirebaseFirestore.instance
          .collection('users')
          .where('uid', isEqualTo: user.uid)
          .get();
      if (snap.docs.isNotEmpty) {
        return snap.docs.first.id; // Returns the actual username string
      }
    }
    return "User";
  }

  @override
  Widget build(BuildContext context) {
    // 1. Defined options with 'View History' included
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
                      // 2. Navigation Logic
                      if (option['title'] == 'View History') {
                        Navigator.pop(context); // Close drawer
                        final username = await _fetchUsername();
                        if (context.mounted) {
                          Navigator.push(
                            context,
                            MaterialPageRoute(
                              builder: (context) => InspectionHistoryScreen(username: username),
                            ),
                          );
                        }
                      } else if (option['title'] == 'About') {
                        Navigator.pop(context);
                        showAboutDialog(
                          context: context,
                          applicationName: 'FoodApp',
                          applicationVersion: '1.0.0',
                          children: [const Text('This is a demo app by Alan.')],
                        );
                      } else {
                        Navigator.pop(context);
                      }
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
                  MaterialPageRoute(builder: (context) => BLEScannerPage()),
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
}*/

import 'package:flutter/material.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:cloud_firestore/cloud_firestore.dart'; 
//import 'package:foodapp/pages/BLEScannerPage.dart';
import 'package:foodapp/pages/InspectionHistoryScreen.dart'; // Make sure this file exists
import 'package:foodapp/pages/blutoothmod.dart';
class HomePage extends StatelessWidget {
  const HomePage({super.key});

  // Helper to fetch the username (which acts as our unique Document ID)
  Future<String> _fetchUsername() async {
    final user = FirebaseAuth.instance.currentUser;
    if (user != null) {
      final snap = await FirebaseFirestore.instance
          .collection('users')
          .where('uid', isEqualTo: user.uid)
          .get();
      if (snap.docs.isNotEmpty) {
        return snap.docs.first.id; // Returns the actual username string
      }
    }
    return "User";
  }

  @override
  Widget build(BuildContext context) {
    // 1. Defined options with 'View History' included
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
                      // 2. Navigation Logic
                      if (option['title'] == 'View History') {
                        Navigator.pop(context); // Close drawer
                        final username = await _fetchUsername();
                        if (context.mounted) {
                          Navigator.push(
                            context,
                            MaterialPageRoute(
                              builder: (context) => InspectionHistoryScreen(username: username),
                            ),
                          );
                        }
                      } else if (option['title'] == 'About') {
                        Navigator.pop(context);
                        showAboutDialog(
                          context: context,
                          applicationName: 'FoodApp',
                          applicationVersion: '1.0.0',
                          children: [const Text('This is a demo app by Alan.')],
                        );
                      } else {
                        Navigator.pop(context);
                      }
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
                  MaterialPageRoute(builder: (context) => BLEScannerPage()),
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