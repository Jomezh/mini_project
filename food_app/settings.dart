/*import 'package:flutter/material.dart';
import 'package:firebase_auth/firebase_auth.dart';

class SettingsPage extends StatefulWidget {
  const SettingsPage({super.key});

  @override
  State<SettingsPage> createState() => _SettingsPageState();
}

class _SettingsPageState extends State<SettingsPage> {
  bool _isNotificationsEnabled = true;
  bool _isAutoConnectEnabled = false;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Settings'),
        elevation: 0,
      ),
      body: ListView(
        children: [
          _buildSectionHeader('Device Connectivity'),
          ListTile(
            leading: const Icon(Icons.router),
            title: const Text('Raspberry Pi Status'),
            subtitle: const Text('Connected via minik:// protocol'),
            trailing: const Icon(Icons.check_circle, color: Colors.green),
            onTap: () {
              // Navigate to Device Pairing / QR Scanner
            },
          ),
          SwitchListTile(
            secondary: const Icon(Icons.settings_input_antenna),
            title: const Text('Auto-connect to Pi'),
            subtitle: const Text('Scan for local hotspot on app start'),
            value: _isAutoConnectEnabled,
            onChanged: (bool value) {
              setState(() => _isAutoConnectEnabled = value);
            },
          ),
          
          const Divider(),
          _buildSectionHeader('Monitoring & Alerts'),
          SwitchListTile(
            secondary: const Icon(Icons.notifications_active),
            title: const Text('Push Notifications'),
            subtitle: const Text('Alerts for MQ sensor threshold breaches'),
            value: _isNotificationsEnabled,
            onChanged: (bool value) {
              setState(() => _isNotificationsEnabled = value);
            },
          ),
          ListTile(
            leading: const Icon(Icons.history),
            title: const Text('Clear Inspection History'),
            onTap: () => _confirmClearHistory(context),
          ),

          const Divider(),
          _buildSectionHeader('Account'),
          ListTile(
            leading: const Icon(Icons.person),
            title: const Text('Profile Details'),
            subtitle: Text(FirebaseAuth.instance.currentUser?.email ?? 'User'),
          ),
          ListTile(
            leading: const Icon(Icons.logout, color: Colors.redAccent),
            title: const Text('Sign Out', style: TextStyle(color: Colors.redAccent)),
            onTap: () async {
              await FirebaseAuth.instance.signOut();
              if (mounted) Navigator.of(context).pushReplacementNamed('/login');
            },
          ),
        ],
      ),
    );
  }

  Widget _buildSectionHeader(String title) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
      child: Text(
        title,
        style: TextStyle(
          fontSize: 14,
          fontWeight: FontWeight.bold,
          color: Theme.of(context).colorScheme.primary,
        ),
      ),
    );
  }

  void _confirmClearHistory(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Clear History?'),
        content: const Text('This will delete all past sensor analysis logs from Firestore.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('Cancel')),
          TextButton(
            onPressed: () {
              // Add Firestore deletion logic for 'inspections' collection
              Navigator.pop(context);
            }, 
            child: const Text('Clear', style: TextStyle(color: Colors.red)),
          ),
        ],
      ),
    );
  }
}*/


import 'package:flutter/material.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:cloud_firestore/cloud_firestore.dart';

class SettingsPage extends StatefulWidget {
  const SettingsPage({super.key});

  @override
  State<SettingsPage> createState() => _SettingsPageState();
}

class _SettingsPageState extends State<SettingsPage> {
  bool _isNotificationsEnabled = true;
  bool _isAutoConnectEnabled = false;
  bool _isDeleting = false;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Settings'),
        elevation: 0,
      ),
      body: ListView(
        children: [
          _buildSectionHeader('Device Connectivity'),
          ListTile(
            leading: const Icon(Icons.router),
            title: const Text('Raspberry Pi Status'),
            subtitle: const Text('Connected via minik:// protocol'),
            trailing: const Icon(Icons.check_circle, color: Colors.green),
          ),
          SwitchListTile(
            secondary: const Icon(Icons.settings_input_antenna),
            title: const Text('Auto-connect to Pi'),
            value: _isAutoConnectEnabled,
            onChanged: (val) => setState(() => _isAutoConnectEnabled = val),
          ),
          
          const Divider(),
          _buildSectionHeader('Monitoring & Alerts'),
          SwitchListTile(
            secondary: const Icon(Icons.notifications_active),
            title: const Text('Push Notifications'),
            value: _isNotificationsEnabled,
            onChanged: (val) => setState(() => _isNotificationsEnabled = val),
          ),
          ListTile(
            leading: const Icon(Icons.history, color: Colors.orange),
            title: const Text('Clear Inspection History'),
            subtitle: const Text('Delete logs linked to your username'),
            onTap: () => _confirmClearHistory(context),
          ),

          const Divider(),
          _buildSectionHeader('Account'),
          ListTile(
            leading: const Icon(Icons.person),
            title: const Text('Profile Details'),
            subtitle: Text(FirebaseAuth.instance.currentUser?.email ?? 'User'),
          ),
          ListTile(
            leading: const Icon(Icons.logout, color: Colors.redAccent),
            title: const Text('Sign Out', style: TextStyle(color: Colors.redAccent)),
            onTap: () async {
              await FirebaseAuth.instance.signOut();
              if (mounted) Navigator.of(context).pushReplacementNamed('/login');
            },
          ),
        ],
      ),
    );
  }

  Widget _buildSectionHeader(String title) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
      child: Text(
        title,
        style: TextStyle(
          fontSize: 14,
          fontWeight: FontWeight.bold,
          color: Theme.of(context).colorScheme.primary,
        ),
      ),
    );
  }

  Future<void> _deleteUserHistory() async {
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) return;

    try {
      // 1. Get the username from the 'users' collection using UID
      final userQuery = await FirebaseFirestore.instance
          .collection('users')
          .where('uid', isEqualTo: user.uid)
          .limit(1)
          .get();

      if (userQuery.docs.isEmpty) {
        _showSnackBar('Could not find username for this account.');
        return;
      }

      // We assume your 'users' document ID is the username
      // If it's a field, use: userQuery.docs.first.get('username')
      final String currentUsername = userQuery.docs.first.id;

      // 2. Query 'inspection' collection for that username
      final inspectionQuery = await FirebaseFirestore.instance
          .collection('inspection')
          .where('username', isEqualTo: currentUsername)
          .get();

      if (inspectionQuery.docs.isEmpty) {
        _showSnackBar('No history found for $currentUsername.');
        return;
      }

      // 3. Batch delete
      final batch = FirebaseFirestore.instance.batch();
      for (var doc in inspectionQuery.docs) {
        batch.delete(doc.reference);
      }

      await batch.commit();
      _showSnackBar('All history for $currentUsername has been deleted.');
      
    } catch (e) {
      debugPrint("Delete error: $e");
      _showSnackBar('Error: ${e.toString()}');
    }
  }

  void _showSnackBar(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(message)));
  }

  void _confirmClearHistory(BuildContext context) {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => StatefulBuilder(
        builder: (context, setDialogState) {
          return AlertDialog(
            title: const Text('Clear History?'),
            content: _isDeleting 
              ? const SizedBox(height: 60, child: Center(child: CircularProgressIndicator()))
              : const Text('This will delete every inspection log associated with your username. This cannot be undone.'),
            actions: _isDeleting ? [] : [
              TextButton(onPressed: () => Navigator.pop(context), child: const Text('Cancel')),
              TextButton(
                onPressed: () async {
                  setDialogState(() => _isDeleting = true);
                  await _deleteUserHistory();
                  if (mounted) {
                    setDialogState(() => _isDeleting = false);
                    Navigator.pop(context);
                  }
                }, 
                child: const Text('Clear All', style: TextStyle(color: Colors.red)),
              ),
            ],
          );
        }
      ),
    );
  }
}