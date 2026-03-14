/*
import 'package:flutter/material.dart';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:firebase_auth/firebase_auth.dart'; // Keep this import if you eventually get currentUserId from FirebaseAuth

class InspectionHistoryScreen extends StatefulWidget {
  final String username; // Declare the username parameter

  // Constructor to accept the username
  const InspectionHistoryScreen({Key? key, required this.username}) : super(key: key);

  @override
  _InspectionHistoryScreenState createState() => _InspectionHistoryScreenState();
}

class _InspectionHistoryScreenState extends State<InspectionHistoryScreen> {
  final FirebaseFirestore _firestore = FirebaseFirestore.instance;

  @override
  Widget build(BuildContext context) {
    // Use widget.username to access the passed parameter
    if (widget.username.isEmpty) {
      return Scaffold(
        appBar: AppBar(title: Text('Inspection History')),
        body: Center(
          child: Text('Invalid user ID. Please ensure you are logged in or provide a valid username.'),
        ),
      );
    }

    return Scaffold(
      appBar: AppBar(title: Text('${widget.username}\'s Inspection History')), // Display the username in the app bar
      body: StreamBuilder<QuerySnapshot>(
        stream: _firestore
            .collection('inspections')
            // Now filtering by the username passed to the screen
            .where('User_ID', isEqualTo: widget.username)
            .orderBy('Time_Stamp', descending: true)
            .snapshots(),
        builder: (context, snapshot) {
          if (snapshot.hasError) {
            return Center(child: Text('Error loading inspections: ${snapshot.error}'));
          }

          if (snapshot.connectionState == ConnectionState.waiting) {
            return Center(child: CircularProgressIndicator());
          }

          if (!snapshot.hasData || snapshot.data!.docs.isEmpty) {
            return Center(child: Text('No inspections found for ${widget.username}.'));
          }

          return ListView.builder(
            itemCount: snapshot.data!.docs.length,
            itemBuilder: (context, index) {
              DocumentSnapshot document = snapshot.data!.docs[index];
              Map<String, dynamic> data = document.data()! as Map<String, dynamic>;

              return Card(
                margin: EdgeInsets.all(8.0),
                child: Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Inspection ID: ${document.id}',
                        style: TextStyle(fontWeight: FontWeight.bold),
                      ),
                      SizedBox(height: 4),
                      Text('User ID: ${data['User_ID'] ?? 'N/A'}'),
                      Text('Timestamp: ${data['Time_Stamp'] != null ? (data['Time_Stamp'] as Timestamp).toDate().toString() : 'N/A'}'),
                      // Add other inspection-related fields here
                      // Text('Location: ${data['location'] ?? 'N/A'}'),
                      // Text('Status: ${data['status'] ?? 'N/A'}'),
                    ],
                  ),
                ),
              );
            },
          );
        },
      ),
    );
  }
}
*/
/*
import 'package:flutter/material.dart';
import 'package:cloud_firestore/cloud_firestore.dart';

class InspectionHistoryScreen extends StatefulWidget {
  final String username;

  const InspectionHistoryScreen({Key? key, required this.username}) : super(key: key);

  @override
  _InspectionHistoryScreenState createState() => _InspectionHistoryScreenState();
}

class _InspectionHistoryScreenState extends State<InspectionHistoryScreen> {
  final FirebaseFirestore _firestore = FirebaseFirestore.instance;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Global Inspection History'),
        backgroundColor: Colors.blueAccent,
      ),
      body: StreamBuilder<QuerySnapshot>(
        // REMOVED .where() to show all documents in the collection
        stream: _firestore
            .collection('inspection')
            .orderBy('Time_Stamp', descending: true)
            .snapshots(),
        builder: (context, snapshot) {
          if (snapshot.hasError) {
            return Center(child: Text('Error: ${snapshot.error}'));
          }

          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }

          if (!snapshot.hasData || snapshot.data!.docs.isEmpty) {
            return const Center(child: Text('No inspections found in database.'));
          }

          return ListView.builder(
            itemCount: snapshot.data!.docs.length,
            itemBuilder: (context, index) {
              DocumentSnapshot document = snapshot.data!.docs[index];
              Map<String, dynamic> data = document.data()! as Map<String, dynamic>;

              // Format the timestamp nicely
              String formattedDate = 'N/A';
              if (data['Time_Stamp'] != null) {
                formattedDate = (data['Time_Stamp'] as Timestamp).toDate().toString().split('.')[0];
              }

              return Card(
                margin: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                elevation: 4,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                child: ExpansionTile(
                  leading: CircleAvatar(
                    backgroundColor: _getSeverityColor(data['Spoilage_Level']),
                    child: const Icon(Icons.analytics, color: Colors.white),
                  ),
                  title: Text('Result: ${data['Spoilage_Level'] ?? 'Unknown'}'),
                  subtitle: Text('Date: $formattedDate'),
                  children: [
                    Padding(
                      padding: const EdgeInsets.all(16.0),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Divider(),
                          _infoRow(Icons.person, 'Inspected By', data['username']),
                          _infoRow(Icons.developer_board, 'Device ID', data['device_id']),
                          _infoRow(Icons.fingerprint, 'Document ID', document.id),
                          const SizedBox(height: 10),
                          Center(
                            child: ElevatedButton.icon(
                              onPressed: () {
                                // TODO: Navigate to Sensor Detail Page using document.id
                              },
                              icon: const Icon(Icons.biotech),
                              label: const Text('View Raw Sensor Data'),
                            ),
                          )
                        ],
                      ),
                    )
                  ],
                ),
              );
            },
          );
        },
      ),
    );
  }

  // Helper to show a row of info
  Widget _infoRow(IconData icon, String label, dynamic value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4.0),
      child: Row(
        children: [
          Icon(icon, size: 20, color: Colors.grey[600]),
          const SizedBox(width: 10),
          Text('$label: ', style: const TextStyle(fontWeight: FontWeight.bold)),
          Expanded(child: Text('${value ?? 'N/A'}', overflow: TextOverflow.ellipsis)),
        ],
      ),
    );
  }

  // Color coding based on your Spoilage Level logic
  Color _getSeverityColor(dynamic level) {
    String s = level.toString().toLowerCase();
    if (s.contains('high') || s.contains('bad')) return Colors.red;
    if (s.contains('medium') || s.contains('warning')) return Colors.orange;
    return Colors.green;
  }
}*/
/*
import 'package:flutter/material.dart';
import 'package:cloud_firestore/cloud_firestore.dart';

class InspectionHistoryScreen extends StatefulWidget {
  final String username;

  const InspectionHistoryScreen({Key? key, required this.username}) : super(key: key);

  @override
  _InspectionHistoryScreenState createState() => _InspectionHistoryScreenState();
}

class _InspectionHistoryScreenState extends State<InspectionHistoryScreen> {
  final FirebaseFirestore _firestore = FirebaseFirestore.instance;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('${widget.username}\'s History'),
        backgroundColor: Colors.blueAccent,
      ),
      body: StreamBuilder<QuerySnapshot>(
        // 1. Filtering by the username passed to this screen
        // 2. Sorting by Time_Stamp (requires a Composite Index)
        stream: _firestore
            .collection('inspection') 
            .where('username', isEqualTo: widget.username)
            .orderBy('Time_Stamp', descending: true)
            .snapshots(),
        builder: (context, snapshot) {
          // If you see a URL in your debug console, CLICK IT to create the index!
          if (snapshot.hasError) {
            return Center(
              child: Padding(
                padding: const EdgeInsets.all(20.0),
                child: Text('Error: ${snapshot.error}', textAlign: TextAlign.center),
              ),
            );
          }

          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }

          if (!snapshot.hasData || snapshot.data!.docs.isEmpty) {
            return Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Icon(Icons.history_toggle_off, size: 60, color: Colors.grey),
                  const SizedBox(height: 10),
                  Text('No inspections found for "${widget.username}"'),
                ],
              ),
            );
          }

          return ListView.builder(
            itemCount: snapshot.data!.docs.length,
            itemBuilder: (context, index) {
              DocumentSnapshot document = snapshot.data!.docs[index];
              Map<String, dynamic> data = document.data()! as Map<String, dynamic>;

              // Safely format the timestamp
              String formattedDate = 'N/A';
              if (data['Time_Stamp'] != null) {
                formattedDate = (data['Time_Stamp'] as Timestamp).toDate().toString().split('.')[0];
              }

              return Card(
                margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                elevation: 4,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(15)),
                child: ExpansionTile(
                  leading: CircleAvatar(
                    backgroundColor: _getSeverityColor(data['Spoilage_Level']),
                    child: const Icon(Icons.analytics, color: Colors.white),
                  ),
                  title: Text(
                    'Result: ${data['Spoilage_Level'] ?? 'Unknown'}',
                    style: const TextStyle(fontWeight: FontWeight.bold),
                  ),
                  subtitle: Text('Date: $formattedDate'),
                  children: [
                    Padding(
                      padding: const EdgeInsets.all(16.0),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Divider(),
                          _infoRow(Icons.person_outline, 'User ID', data['username']),
                          _infoRow(Icons.developer_mode, 'Device ID', data['device_id']),
                          _infoRow(Icons.tag, 'Record ID', document.id),
                          const SizedBox(height: 15),
                          SizedBox(
                            width: double.infinity,
                            child: ElevatedButton.icon(
                              onPressed: () {
                                // TODO: Navigate to Sensor Data Detail page
                                print("Opening details for: ${document.id}");
                              },
                              icon: const Icon(Icons.bar_chart),
                              label: const Text('View Raw Sensor Data'),
                              style: ElevatedButton.styleFrom(
                                backgroundColor: Colors.blueAccent,
                                foregroundColor: Colors.white,
                              ),
                            ),
                          )
                        ],
                      ),
                    )
                  ],
                ),
              );
            },
          );
        },
      ),
    );
  }

  // Helper widget for a clean info layout
  Widget _infoRow(IconData icon, String label, dynamic value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4.0),
      child: Row(
        children: [
          Icon(icon, size: 18, color: Colors.blueGrey),
          const SizedBox(width: 8),
          Text('$label: ', style: const TextStyle(fontWeight: FontWeight.w600)),
          Expanded(
            child: Text(
              '${value ?? 'N/A'}',
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(color: Colors.black87),
            ),
          ),
        ],
      ),
    );
  }

  // Color logic for the status indicator
  Color _getSeverityColor(dynamic level) {
    String s = level.toString().toLowerCase();
    if (s.contains('high') || s.contains('bad') || s.contains('spoiled')) {
      return Colors.redAccent;
    } else if (s.contains('medium') || s.contains('warning')) {
      return Colors.orangeAccent;
    } else if (s.contains('fresh') || s.contains('good') || s.contains('low')) {
      return Colors.greenAccent[700]!;
    }
    return Colors.grey;
  }
}*/
import 'package:flutter/material.dart';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:foodapp/pages/sensordata.dart'; // Ensure this import matches your file path

class InspectionHistoryScreen extends StatefulWidget {
  final String username;

  const InspectionHistoryScreen({super.key, required this.username});

  @override
  State<InspectionHistoryScreen> createState() => _InspectionHistoryScreenState();
}

class _InspectionHistoryScreenState extends State<InspectionHistoryScreen> {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      // Matching the AppBar style of HomePage
      appBar: AppBar(
        title: Text("${widget.username}'s History"),
        centerTitle: true,
        backgroundColor: Colors.blueAccent,
        foregroundColor: Colors.white,
      ),
      body: StreamBuilder<QuerySnapshot>(
        stream: FirebaseFirestore.instance
            .collection('inspection')
            .where('username', isEqualTo: widget.username)
            .orderBy('Time_Stamp', descending: true)
            .snapshots(),
        builder: (context, snapshot) {
          if (snapshot.hasError) {
            return Center(child: Text("Error: ${snapshot.error}"));
          }
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (!snapshot.hasData || snapshot.data!.docs.isEmpty) {
            return const Center(
              child: Text(
                "No history found.",
                style: TextStyle(color: Colors.grey),
              ),
            );
          }

          return ListView.builder(
            padding: const EdgeInsets.all(10),
            itemCount: snapshot.data!.docs.length,
            itemBuilder: (context, index) {
              final doc = snapshot.data!.docs[index];
              final data = doc.data() as Map<String, dynamic>;

              return Card(
                elevation: 3,
                margin: const EdgeInsets.only(bottom: 15),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                child: ExpansionTile(
                  leading: Icon(
                    Icons.analytics,
                    color: _getSeverityColor(data['Spoilage_Level']),
                    size: 30,
                  ),
                  title: Text(
                    "Result: ${data['Spoilage_Level'] ?? 'Unknown'}",
                    style: const TextStyle(fontWeight: FontWeight.bold),
                  ),
                  subtitle: Text("ID: ${doc.id}"),
                  children: [
                    Padding(
                      padding: const EdgeInsets.all(16.0),
                      child: Column(
                        children: [
                          _buildDetailRow(Icons.calendar_today, "Date", _formatTimestamp(data['Time_Stamp'])),
                          _buildDetailRow(Icons.developer_board, "Device", data['device_id']),
                          const SizedBox(height: 20),
                          // Button styled exactly like the "Pair Device" button on HomePage
                          SizedBox(
                            width: double.infinity,
                            child: ElevatedButton.icon(
                              style: ElevatedButton.styleFrom(
                                backgroundColor: Colors.blueAccent,
                                padding: const EdgeInsets.symmetric(vertical: 12),
                                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                              ),
                              onPressed: () {
                                Navigator.push(
                                  context,
                                  MaterialPageRoute(
                                    builder: (context) => SensorDataScreen(inspectionId: doc.id),
                                  ),
                                );
                              },
                              icon: const Icon(Icons.bar_chart, color: Colors.white),
                              label: const Text("View Raw Data", style: TextStyle(color: Colors.white)),
                            ),
                          ),
                        ],
                      ),
                    )
                  ],
                ),
              );
            },
          );
        },
      ),
    );
  }

  // Helper for consistent detail rows
  Widget _buildDetailRow(IconData icon, String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          Icon(icon, size: 18, color: Colors.blueAccent),
          const SizedBox(width: 10),
          Text("$label: ", style: const TextStyle(fontWeight: FontWeight.bold)),
          Text(value),
        ],
      ),
    );
  }

  String _formatTimestamp(dynamic ts) {
    if (ts == null) return "N/A";
    return (ts as Timestamp).toDate().toString().split('.')[0];
  }

  Color _getSeverityColor(dynamic level) {
    String s = level.toString().toLowerCase();
    if (s.contains('high') || s.contains('bad')) return Colors.red;
    if (s.contains('medium')) return Colors.orange;
    return Colors.green;
  }
}
