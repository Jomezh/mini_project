import 'package:flutter/material.dart';
import 'package:cloud_firestore/cloud_firestore.dart';

class SensorDataScreen extends StatelessWidget {
  final String inspectionId;

  const SensorDataScreen({super.key, required this.inspectionId});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("Raw Sensor Data"),
        centerTitle: true,
        backgroundColor: Colors.blueAccent,
        foregroundColor: Colors.white,
      ),
      body: StreamBuilder<QuerySnapshot>(
        stream: FirebaseFirestore.instance
            .collection('sensor_data')
            .where('inspection_id', isEqualTo: inspectionId)
            .snapshots(),
        builder: (context, snapshot) {
          if (snapshot.hasError) return Center(child: Text("Error: ${snapshot.error}"));
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (!snapshot.hasData || snapshot.data!.docs.isEmpty) {
            return const Center(child: Text("No sensor records found.", style: TextStyle(color: Colors.grey)));
          }

          return ListView.builder(
            padding: const EdgeInsets.all(12),
            itemCount: snapshot.data!.docs.length,
            itemBuilder: (context, index) {
              final data = snapshot.data!.docs[index].data() as Map<String, dynamic>;

              return Column(
                children: [
                  // 1. Environmental Section (Temp & Humidity)
                  Row(
                    children: [
                      _buildMainStatCard("Temperature", "${data['temperature']}°C", Icons.thermostat, Colors.orange),
                      _buildMainStatCard("Humidity", "${data['humidity']}%", Icons.water_drop, Colors.blue),
                    ],
                  ),
                  const SizedBox(height: 12),
                  
                  // 2. Gas Sensor Grid (MQ Series)
                  const Padding(
                    padding: EdgeInsets.symmetric(vertical: 8.0),
                    child: Text("Gas Sensor Array (ppm)", style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                  ),
                  GridView.count(
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    crossAxisCount: 3,
                    childAspectRatio: 1.2,
                    mainAxisSpacing: 8,
                    crossAxisSpacing: 8,
                    children: [
                      _buildGasTile("MQ135", data['mq135']),
                      _buildGasTile("MQ136", data['mq136']),
                      _buildGasTile("MQ2", data['mq2']),
                      _buildGasTile("MQ3", data['mq3']),
                      _buildGasTile("MQ4", data['mq4']),
                      _buildGasTile("MQ5", data['mq5']),
                      _buildGasTile("MQ6", data['mq6']),
                      _buildGasTile("MQ8", data['mq8']),
                      _buildGasTile("MQ9", data['mq9']),
                    ],
                  ),
                  const Divider(height: 40),
                ],
              );
            },
          );
        },
      ),
    );
  }

  // Large card for Temp/Humidity
  Widget _buildMainStatCard(String label, String value, IconData icon, Color color) {
    return Expanded(
      child: Card(
        elevation: 4,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Column(
            children: [
              Icon(icon, color: color, size: 30),
              const SizedBox(height: 8),
              Text(label, style: const TextStyle(fontSize: 12, color: Colors.grey)),
              Text(value, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            ],
          ),
        ),
      ),
    );
  }

  // Small tile for the MQ gas sensors
  Widget _buildGasTile(String name, dynamic value) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.blueAccent.withOpacity(0.1),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.blueAccent.withOpacity(0.3)),
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text(name, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.blueAccent)),
          const SizedBox(height: 4),
          Text(value?.toString() ?? "0.0", style: const TextStyle(fontSize: 14)),
        ],
      ),
    );
  }
}