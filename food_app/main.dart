import 'package:flutter/material.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:cloud_firestore/cloud_firestore.dart';
import 'firebase_options.dart';
import 'pages/signup.dart'; 
import 'pages/homepage.dart'; 

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Firebase.initializeApp(options: DefaultFirebaseOptions.currentPlatform);
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      theme: ThemeData(useMaterial3: true, colorSchemeSeed: Colors.blue),
      home: StreamBuilder<User?>(
        stream: FirebaseAuth.instance.authStateChanges(),
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Scaffold(body: Center(child: CircularProgressIndicator()));
          }
          // If logged in, show HomePage. If not, show AuthPage (Login)
          return snapshot.hasData ? const HomePage() : const AuthPage();
        },
      ),
    );
  }
}

class AuthPage extends StatefulWidget {
  const AuthPage({super.key});
  @override
  State<AuthPage> createState() => _AuthPageState();
}

class _AuthPageState extends State<AuthPage> {
  final identifierController = TextEditingController();
  final passwordController = TextEditingController();
  bool loading = false;

  void login() async {
    String input = identifierController.text.trim();
    String password = passwordController.text.trim();

    if (input.isEmpty || password.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text("Please fill in all fields")));
      return;
    }

    setState(() => loading = true);

    try {
      String emailToAuth = input;

      // If input is a Username (no @), find the email in Firestore
      if (!input.contains('@')) {
        final userQuery = await FirebaseFirestore.instance
            .collection('users')
            .where('username', isEqualTo: input.toLowerCase())
            .get();

        if (userQuery.docs.isEmpty) {
          throw FirebaseAuthException(code: 'user-not-found', message: "User ID not found.");
        }
        emailToAuth = userQuery.docs.first.get('email');
      }

      await FirebaseAuth.instance.signInWithEmailAndPassword(
        email: emailToAuth,
        password: password,
      );
      
    } on FirebaseAuthException catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.message ?? "Login Failed")));
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(25),
          child: Column(
            children: [
              const Icon(Icons.lock_person, size: 80, color: Colors.blue),
              const SizedBox(height: 20),
              const Text("Login", style: TextStyle(fontSize: 32, fontWeight: FontWeight.bold)),
              const SizedBox(height: 30),
              TextField(
                controller: identifierController, 
                decoration: const InputDecoration(labelText: "Email or User ID", border: OutlineInputBorder()),
              ),
              const SizedBox(height: 15),
              TextField(
                controller: passwordController, 
                obscureText: true, 
                decoration: const InputDecoration(labelText: "Password", border: OutlineInputBorder()),
              ),
              const SizedBox(height: 25),
              loading 
                ? const CircularProgressIndicator()
                : SizedBox(
                    width: double.infinity,
                    height: 55,
                    child: ElevatedButton(onPressed: login, child: const Text("Login")),
                  ),
              TextButton(
                onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (context) => const SignUpPage())),
                child: const Text("Don't have an account? Sign Up"),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
/*
import 'dart:async';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter_background_service/flutter_background_service.dart';
import 'package:flutter_background_service_android/flutter_background_service_android.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'firebase_options.dart';
import 'pages/signup.dart'; 
import 'pages/homepage.dart'; 

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Firebase.initializeApp(options: DefaultFirebaseOptions.currentPlatform);
  await initializeBackgroundService();
  runApp(const MyApp());
}

Future<void> initializeBackgroundService() async {
  final service = FlutterBackgroundService();

  const AndroidNotificationChannel channel = AndroidNotificationChannel(
    'minik_service', 
    'MiniK Data Server', 
    description: 'HTTP server for Raspberry Pi',
    importance: Importance.low,
  );

  final FlutterLocalNotificationsPlugin flutterLocalNotificationsPlugin =
      FlutterLocalNotificationsPlugin();

  if (Platform.isAndroid) {
    final AndroidFlutterLocalNotificationsPlugin? androidImplementation =
        flutterLocalNotificationsPlugin.resolvePlatformSpecificImplementation<
            AndroidFlutterLocalNotificationsPlugin>();

    await androidImplementation?.createNotificationChannel(channel);
  }

  await service.configure(
    androidConfiguration: AndroidConfiguration(
      onStart: onStart,
      autoStart: true,
      isForegroundMode: true,
      notificationChannelId: 'minik_service',
      initialNotificationTitle: 'MiniK Data Server',
      initialNotificationContent: 'Listening for Pi 02W...',
      foregroundServiceNotificationId: 888,
      // ✅ FIXED: Remove foregroundServiceTypes completely
    ),
    iosConfiguration: IosConfiguration(
      autoStart: true,
      onForeground: onStart,
      onBackground: onIosBackground,
    ),
  );
}

@pragma('vm:entry-point')
bool onIosBackground(ServiceInstance service) => true;

@pragma('vm:entry-point')
void onStart(ServiceInstance service) async {
  WidgetsFlutterBinding.ensureInitialized();
  
  if (service is AndroidServiceInstance) {
    service.on('setAsForeground').listen((event) {
      service.setAsForegroundService();
    });
    service.on('setAsBackground').listen((event) {
      service.setAsBackgroundService();
    });
    service.setAsForegroundService();
  }

  service.on('stopService').listen((event) {
    service.stopSelf();
  });

  HttpServer? server;
  try {
    server = await HttpServer.bind(InternetAddress.anyIPv4, 8080, shared: true);
    
    if (service is AndroidServiceInstance) {
      service.setForegroundNotificationInfo(
        title: "MiniK Server Active",
        content: "Listening on port 8080",
      );
    }

    debugPrint('🚀 Server running on port 8080');

    await for (final HttpRequest request in server) {
      if (request.method == 'POST' && request.uri.path == '/upload/image') {
        try {
          final List<int> bytes = await request.fold<List<int>>(
            <int>[],
            (previous, element) => previous..addAll(element),
          );

          debugPrint("📸 Received ${bytes.length} bytes from Pi");

          service.invoke('dataReceived', {
            'size': bytes.length,
            'timestamp': DateTime.now().toIso8601String(),
          });

          request.response
            ..statusCode = 200
            ..write('OK')
            ..close();

        } catch (e) {
          debugPrint('Upload error: $e');
          request.response
            ..statusCode = 500
            ..write('Error')
            ..close();
        }
      } else {
        request.response
          ..statusCode = 200
          ..write('MiniK Server OK')
          ..close();
      }
    }
  } catch (e) {
    debugPrint('Server error: $e');
  }
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      theme: ThemeData(useMaterial3: true, colorSchemeSeed: Colors.blue),
      home: StreamBuilder<User?>(
        stream: FirebaseAuth.instance.authStateChanges(),
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Scaffold(body: Center(child: CircularProgressIndicator()));
          }
          return snapshot.hasData ? const HomePage() : const SignUpPage();
        },
      ),
    );
  }
}
*/