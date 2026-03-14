/*import 'dart:typed_data';
import 'package:flutter/services.dart';
import 'package:image/image.dart' as img; // Requires 'image' package in pubspec
import 'package:tflite_flutter/tflite_flutter.dart';

class ImageClassifier {
  Interpreter? _interpreter;
  List<String> _labels = [];

  // 1. Load the Model and the Labels
  Future<void> loadModel() async {
    try {
      // Load the model from assets
      _interpreter = await Interpreter.fromAsset('assets/food_classifier_model.tflite');
      
      // Load the labels.txt file and split into a list
      final labelString = await rootBundle.loadString('assets/labels.txt');
      _labels = labelString.split('\n').where((s) => s.trim().isNotEmpty).toList();
      
      print("AI: Initialization Successful. Classes: $_labels");
    } catch (e) {
      print("AI: Failed to load model/labels: $e");
    }
  }

  // 2. Process and Classify
  Future<String> classify(Uint8List imageBytes) async {
    if (_interpreter == null || _labels.isEmpty) return "Model not ready";

    try {
      // STEP A: Decode the image and resize to 224x224
      img.Image? originalImage = img.decodeImage(imageBytes);
      if (originalImage == null) return "Invalid Image Data";
      
      img.Image resizedImage = img.copyResize(originalImage, width: 224, height: 224);

      // STEP B: Convert image to Float32 List and Normalize (1/255.0)
      // We need a 4D array: [batch, height, width, channels] -> [1, 224, 224, 3]
      var input = List.generate(1 * 224 * 224 * 3, (_) => 0.0).reshape([1, 224, 224, 3]);

      for (var y = 0; y < 224; y++) {
        for (var x = 0; x < 224; x++) {
          var pixel = resizedImage.getPixel(x, y);
          
          // Normalizing pixels to 0.0 - 1.0 range as used in your .ipynb training
          input[0][y][x][0] = pixel.r / 255.0; // Red
          input[0][y][x][1] = pixel.g / 255.0; // Green
          input[0][y][x][2] = pixel.b / 255.0; // Blue
        }
      }

      // STEP C: Prepare Output Tensor [1, 2]
      // Based on your categorical training (Beef, Other)
      var output = List.filled(1 * _labels.length, 0.0).reshape([1, _labels.length]);

      // STEP D: Run the "Inference"
      _interpreter!.run(input, output);

      // STEP E: Find the index with the highest probability
      int highestIndex = 0;
      double maxConfidence = -1.0;

      for (int i = 0; i < _labels.length; i++) {
        if (output[0][i] > maxConfidence) {
          maxConfidence = output[0][i];
          highestIndex = i;
        }
      }

      // Optional: Add confidence percentage to the string
      String confidencePercent = (maxConfidence * 100).toStringAsFixed(1);
      return "${_labels[highestIndex]} ($confidencePercent%)";

    } catch (e) {
      print("AI: Classification Error: $e");
      return "Error during analysis";
    }
  }

  // Clean up memory when the app page is closed
  void dispose() {
    _interpreter?.close();
  }
}*/
/*
import 'dart:typed_data';
import 'package:flutter/material.dart';

class ImageClassificationPage extends StatefulWidget {
  // This requires the image data to be passed in when the page is created
  final Uint8List imageData;

  const ImageClassificationPage({
    super.key,
    required this.imageData,
  });

  @override
  State<ImageClassificationPage> createState() => _ImageClassificationPageState();
}

class _ImageClassificationPageState extends State<ImageClassificationPage> {
  bool _isClassifying = false;
  String _classificationResult = "Awaiting classification...";

  @override
  void initState() {
    super.initState();
    // Automatically start classifying when the page loads
    _runClassification();
  }

  Future<void> _runClassification() async {
    setState(() {
      _isClassifying = true;
    });

    // TODO: Insert your actual ML classification logic here!
    // Example: Use TFLite to process widget.imageData
    // For now, we simulate a 2-second delay to mock the process
    await Future.delayed(const Duration(seconds: 2));

    if (mounted) {
      setState(() {
        _isClassifying = false;
        _classificationResult = "Detected: Example Object (98.5%)"; // Replace with real result
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("Image Classification"),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            // Display the received image
            ClipRRect(
              borderRadius: BorderRadius.circular(15),
              child: Image.memory(
                widget.imageData,
                height: 300,
                width: double.infinity,
                fit: BoxFit.cover,
              ),
            ),
            const SizedBox(height: 30),
            
            // Status and Results Area
            const Text(
              "Classification Result",
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.blueGrey),
            ),
            const SizedBox(height: 15),
            
            if (_isClassifying)
              const Column(
                children: [
                  CircularProgressIndicator(),
                  SizedBox(height: 10),
                  Text("Analyzing image..."),
                ],
              )
            else
              Container(
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(
                  color: Colors.green[50],
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: Colors.green),
                ),
                child: Text(
                  _classificationResult,
                  style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: Colors.green),
                  textAlign: TextAlign.center,
                ),
              ),

            const SizedBox(height: 30),
            ElevatedButton.icon(
              onPressed: _runClassification, 
              icon: const Icon(Icons.refresh), 
              label: const Text("Run Again")
            )
          ],
        ),
      ),
    );
  }
}*/
/*
import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:tflite_flutter/tflite_flutter.dart';
import 'package:image/image.dart' as img; // Use the 'image' package for processing
import 'package:flutter/foundation.dart'; // Add this for Isolate
class ImageClassificationPage extends StatefulWidget {
  final Uint8List imageData;

  const ImageClassificationPage({super.key, required this.imageData});

  @override
  State<ImageClassificationPage> createState() => _ImageClassificationPageState();
}

class _ImageClassificationPageState extends State<ImageClassificationPage> {
  bool _isClassifying = false;
  String _classificationResult = "Awaiting classification...";
  Interpreter? _interpreter;

  @override
  void initState() {
    super.initState();
    _loadModel().then((_) => _runClassification());
  }

  // Load the model from assets
  Future<void> _loadModel() async {
    try {
      _interpreter = await Interpreter.fromAsset('assets/food_classifier_model.tflite');
      print("Model loaded successfully");
    } catch (e) {
      print("Error loading model: $e");
    }
  }

  Future<void> _runClassification() async {
    if (_interpreter == null) {
      await _loadModel();
    }

    setState(() => _isClassifying = true);

    try {
      // 1. Preprocess the image (Resize to 224x224 and Normalize)
      // This mimics your Python: img_array /= 255.0
      var input = _preprocessImage(widget.imageData);

      // 2. Prepare output buffer 
      // Your model has 2 classes: [Beef, Others]
      var output = List<double>.filled(2, 0).reshape([1, 2]);

      // 3. Run Inference
      _interpreter!.run(input, output);

      // 4. Extract Results
      double beefConfidence = output[0][0];
      double othersConfidence = output[0][1];

      setState(() {
        if (beefConfidence >= 0.60) { // Using your 60% threshold
          _classificationResult = "✅ BEEF DETECTED\n(${(beefConfidence * 100).toStringAsFixed(1)}%)";
        } else {
          _classificationResult = "❌ NOT RECOGNIZED\n(${(othersConfidence * 100).toStringAsFixed(1)}%)";
        }
      });
    } catch (e) {
      setState(() => _classificationResult = "Error: $e");
    } finally {
      setState(() => _isClassifying = false);
    }
  }

  // HELPER: Convert Uint8List to 4D List [1, 224, 224, 3]
  List<List<List<List<double>>>> _preprocessImage(Uint8List bytes) {
    img.Image? originalImage = img.decodeImage(bytes);
    img.Image resizedImage = img.copyResize(originalImage!, width: 224, height: 224);

    // Create a 4D array: [batch, height, width, channels]
    var input = List.generate(
      1,
      (b) => List.generate(
        224,
        (y) => List.generate(
          224,
          (x) {
            final pixel = resizedImage.getPixel(x, y);
            // Normalize pixels to [0, 1] as per your Python code
            return [
              pixel.r / 255.0,
              pixel.g / 255.0,
              pixel.b / 255.0,
            ];
          },
        ),
      ),
    );
    return input;
  }

  @override
  void dispose() {
    _interpreter?.close();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    // ... (Keep your existing UI code here) ...
    return Scaffold(/* Your existing UI */);
  }
}*/
/*
import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:tflite_flutter/tflite_flutter.dart';
import 'package:image/image.dart' as img; 

class ImageClassificationPage extends StatefulWidget {
  final Uint8List imageData;

  const ImageClassificationPage({super.key, required this.imageData});

  @override
  State<ImageClassificationPage> createState() => _ImageClassificationPageState();
}

class _ImageClassificationPageState extends State<ImageClassificationPage> {
  bool _isClassifying = false;
  String _classificationResult = "Loading model and labels...";
  Interpreter? _interpreter;
  List<String> _labels = [];

  @override
  void initState() {
    super.initState();
    _initializeModelAndLabels();
  }

  // Load both the Model and the Labels file
  Future<void> _initializeModelAndLabels() async {
    try {
      // 1. Load Model
      _interpreter = await Interpreter.fromAsset('assets/food_classifier_model.tflite');
      
      // 2. Load Labels
      final labelData = await DefaultAssetBundle.of(context).loadString('assets/labels.txt');
      _labels = labelData.split('\n').where((s) => s.isNotEmpty).toList();

      print("Model and ${_labels.length} labels loaded.");
      
      // 3. Run initial classification
      _runClassification();
    } catch (e) {
      setState(() => _classificationResult = "Init Error: $e");
    }
  }

  Future<void> _runClassification() async {
    if (_interpreter == null || _labels.isEmpty) return;

    setState(() => _isClassifying = true);

    try {
      // 1. Preprocess (Resize to 224 and normalize 0.0 - 1.0)
      var input = _preprocessImage(widget.imageData);

      // 2. Prepare output buffer based on label count
      // If labels.txt has 2 lines, output is [1, 2]
      var output = List<double>.filled(_labels.length, 0).reshape([1, _labels.length]);

      // 3. Run Inference
      _interpreter!.run(input, output);

      // 4. Find the highest confidence (Argmax logic)
      List<double> results = List<double>.from(output[0]);
      double maxScore = -1.0;
      int bestIndex = -1;

      for (int i = 0; i < results.length; i++) {
        if (results[i] > maxScore) {
          maxScore = results[i];
          bestIndex = i;
        }
      }

      // 5. Update UI with Threshold Logic
      setState(() {
        const double THRESHOLD = 0.60;
        String detectedLabel = _labels[bestIndex].trim();

        if (maxScore >= THRESHOLD) {
          _classificationResult = "✅ MATCH: $detectedLabel\nConfidence: ${(maxScore * 100).toStringAsFixed(1)}%";
        } else {
          _classificationResult = "❌ UNCERTAIN\n(Best guess: $detectedLabel at ${(maxScore * 100).toStringAsFixed(1)}%)";
        }
      });

    } catch (e) {
      setState(() => _classificationResult = "Inference Error: $e");
    } finally {
      setState(() => _isClassifying = false);
    }
  }

  List<List<List<List<double>>>> _preprocessImage(Uint8List bytes) {
    img.Image? originalImage = img.decodeImage(bytes);
    img.Image resizedImage = img.copyResize(originalImage!, width: 224, height: 224);

    return List.generate(1, (b) => List.generate(224, (y) => List.generate(224, (x) {
      final pixel = resizedImage.getPixel(x, y);
      return [pixel.r / 255.0, pixel.g / 255.0, pixel.b / 255.0];
    })));
  }

  @override
  void dispose() {
    _interpreter?.close();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Food Classifier")),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Image.memory(widget.imageData, height: 300),
            const SizedBox(height: 20),
            _isClassifying 
              ? const CircularProgressIndicator() 
              : Text(_classificationResult, 
                  textAlign: TextAlign.center,
                  style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            const SizedBox(height: 20),
            ElevatedButton(
              onPressed: _isClassifying ? null : _runClassification,
              child: const Text("Re-run Classification"),
            )
          ],
        ),
      ),
    );
  }
}*/
import 'dart:typed_data';
import 'dart:math';
import 'package:flutter/material.dart';
import 'package:tflite_flutter/tflite_flutter.dart';
import 'package:image/image.dart' as img;

/// HELPER CLASS: Extracts classification logic for use elsewhere in the app
class ImageClassificationHelper {
  static Future<String?> classifyBytes(Uint8List imageBytes, BuildContext context) async {
    Interpreter? interpreter;
    try {
      // 1. Load Model and Labels
      interpreter = await Interpreter.fromAsset('assets/food_classifier_model.tflite');
      final labelData = await DefaultAssetBundle.of(context).loadString('assets/labels.txt');
      List<String> labels = labelData.split('\n').where((s) => s.isNotEmpty).toList();

      // 2. Preprocess
      img.Image? originalImage = img.decodeImage(imageBytes);
      if (originalImage == null) return null;
      img.Image resizedImage = img.copyResize(originalImage, width: 224, height: 224);

      var input = List.generate(1, (b) => List.generate(224, (y) => List.generate(224, (x) {
        final pixel = resizedImage.getPixel(x, y);
        return [pixel.r / 255.0, pixel.g / 255.0, pixel.b / 255.0];
      })));

      // 3. Run Inference
      var output = List<double>.filled(labels.length, 0).reshape([1, labels.length]);
      interpreter.run(input, output);

      // 4. Argmax
      List<double> results = List<double>.from(output[0]);
      double maxScore = results.reduce(max);
      int bestIndex = results.indexOf(maxScore);

      if (maxScore >= 0.60) {
        return labels[bestIndex].trim();
      }
      return "Unknown";
    } catch (e) {
      debugPrint('[ImageClassificationHelper] Error: $e');
      return null;
    } finally {
      interpreter?.close();
    }
  }
}

class ImageClassificationPage extends StatefulWidget {
  final Uint8List imageData;

  const ImageClassificationPage({super.key, required this.imageData});

  @override
  State<ImageClassificationPage> createState() => _ImageClassificationPageState();
}

class _ImageClassificationPageState extends State<ImageClassificationPage> {
  bool _isClassifying = false;
  String _classificationResult = "Loading model and labels...";
  Interpreter? _interpreter;
  List<String> _labels = [];

  @override
  void initState() {
    super.initState();
    _initializeModelAndLabels();
  }

  Future<void> _initializeModelAndLabels() async {
    try {
      _interpreter = await Interpreter.fromAsset('assets/food_classifier_model.tflite');
      final labelData = await DefaultAssetBundle.of(context).loadString('assets/labels.txt');
      _labels = labelData.split('\n').where((s) => s.isNotEmpty).toList();

      debugPrint("Model and ${_labels.length} labels loaded.");
      _runClassification();
    } catch (e) {
      setState(() => _classificationResult = "Init Error: $e");
    }
  }

  Future<void> _runClassification() async {
    if (_interpreter == null || _labels.isEmpty) return;

    setState(() => _isClassifying = true);

    try {
      var input = _preprocessImage(widget.imageData);
      var output = List<double>.filled(_labels.length, 0).reshape([1, _labels.length]);

      _interpreter!.run(input, output);

      List<double> results = List<double>.from(output[0]);
      double maxScore = results.reduce(max);
      int bestIndex = results.indexOf(maxScore);

      setState(() {
        const double threshold = 0.60;
        String detectedLabel = _labels[bestIndex].trim();

        if (maxScore >= threshold) {
          _classificationResult = "✅ MATCH: $detectedLabel\nConfidence: ${(maxScore * 100).toStringAsFixed(1)}%";
        } else {
          _classificationResult = "❌ UNCERTAIN\n(Best guess: $detectedLabel at ${(maxScore * 100).toStringAsFixed(1)}%)";
        }
      });
    } catch (e) {
      setState(() => _classificationResult = "Inference Error: $e");
    } finally {
      setState(() => _isClassifying = false);
    }
  }

  List<List<List<List<double>>>> _preprocessImage(Uint8List bytes) {
    img.Image? originalImage = img.decodeImage(bytes);
    img.Image resizedImage = img.copyResize(originalImage!, width: 224, height: 224);

    return List.generate(1, (b) => List.generate(224, (y) => List.generate(224, (x) {
      final pixel = resizedImage.getPixel(x, y);
      return [pixel.r / 255.0, pixel.g / 255.0, pixel.b / 255.0];
    })));
  }

  @override
  void dispose() {
    _interpreter?.close();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("Food Classifier"),
        backgroundColor: Colors.blueAccent,
      ),
      body: Center(
        child: SingleChildScrollView(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              ClipRRect(
                borderRadius: BorderRadius.circular(15),
                child: Image.memory(widget.imageData, height: 300, fit: BoxFit.cover),
              ),
              const SizedBox(height: 30),
              _isClassifying 
                ? const CircularProgressIndicator() 
                : Container(
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(12),
                      boxShadow: [BoxShadow(color: Colors.black12, blurRadius: 8)],
                    ),
                    child: Text(_classificationResult, 
                        textAlign: TextAlign.center,
                        style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                  ),
              const SizedBox(height: 30),
              ElevatedButton.icon(
                onPressed: _isClassifying ? null : _runClassification,
                icon: const Icon(Icons.refresh),
                label: const Text("Re-run Classification"),
                style: ElevatedButton.styleFrom(padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12)),
              )
            ],
          ),
        ),
      ),
    );
  }
}