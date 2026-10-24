import 'package:flutter/material.dart';
import '../services/task_service.dart';

class TaskDashboardScreen extends StatefulWidget {
  const TaskDashboardScreen({super.key});

  @override
  State<TaskDashboardScreen> createState() => _TaskDashboardScreenState();
}

class _TaskDashboardScreenState extends State<TaskDashboardScreen> {
  final TaskService _taskService = TaskService();
  List<dynamic> _tasks = [];
  bool _loading = true;
  String _selectedStatus = "pending"; // Default to pending tasks

  @override
  void initState() {
    super.initState();
    _loadTasks();
  }

  Future<void> _loadTasks() async {
    setState(() => _loading = true);
    try {
      final tasks = await _taskService.getTasks(status: _selectedStatus);
      setState(() {
        _tasks = tasks;
        _loading = false;
      });
    } catch (e) {
      setState(() => _loading = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("Error loading tasks: $e")),
      );
    }
  }

  Color _getPriorityColor(String? priority) {
    switch (priority?.toLowerCase()) {
      case 'high':
        return Colors.red;
      case 'medium':
        return Colors.orange;
      case 'low':
      default:
        return Colors.green;
    }
  }

  Future<void> _toggleTaskStatus(String taskId, String currentStatus) async {
    final newStatus = currentStatus == "pending" ? "completed" : "pending";
    try {
      await _taskService.updateTaskStatus(taskId, newStatus);
      await _loadTasks();
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("Failed to update status: $e")),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("Actionable Tasks & Priorities"),
        actions: [
          PopupMenuButton<String>(
            onSelected: (value) { // <-- Fixed from onSelect to onSelected
              setState(() => _selectedStatus = value);
              _loadTasks();
            },
            itemBuilder: (context) => [
              const PopupMenuItem(value: "pending", child: Text("Pending Tasks")),
              const PopupMenuItem(value: "completed", child: Text("Completed")),
              const PopupMenuItem(value: "dismissed", child: Text("Dismissed")),
            ],
            icon: const Icon(Icons.filter_list),
          ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _tasks.isEmpty
              ? const Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.task_alt, size: 64, color: Colors.grey),
                      SizedBox(height: 16),
                      Text("No tasks found in this view."),
                    ],
                  ),
                )
              : ListView.builder(
                  itemCount: _tasks.length,
                  itemBuilder: (context, index) {
                    final task = _tasks[index];
                    final priority = task["priority"] ?? "medium";
                    final priorityColor = _getPriorityColor(priority);

                    return Card(
                      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
                      child: ListTile(
                        leading: Checkbox(
                          value: task["status"] == "completed",
                          onChanged: (val) => _toggleTaskStatus(task["id"], task["status"]),
                        ),
                        title: Text(
                          task["title"] ?? "Untitled Task",
                          style: TextStyle(
                            fontWeight: FontWeight.bold,
                            decoration: task["status"] == "completed"
                                ? TextDecoration.lineThrough
                                : null,
                          ),
                        ),
                        subtitle: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            if (task["description"] != null) ...[
                              const SizedBox(height: 4),
                              Text(task["description"]),
                            ],
                            const SizedBox(height: 6),
                            Row(
                              children: [
                                Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                                  decoration: BoxDecoration(
                                    color: priorityColor.withOpacity(0.1),
                                    border: Border.all(color: priorityColor),
                                    borderRadius: BorderRadius.circular(4),
                                  ),
                                  child: Text(
                                    priority.toUpperCase(),
                                    style: TextStyle(fontSize: 11, color: priorityColor, fontWeight: FontWeight.bold),
                                  ),
                                ),
                                if (task["due_date"] != null) ...[
                                  const SizedBox(width: 12),
                                  const Icon(Icons.calendar_today, size: 12, color: Colors.grey),
                                  const SizedBox(width: 4),
                                  Text(
                                    task["due_date"].toString().split('T')[0],
                                    style: const TextStyle(fontSize: 12, color: Colors.grey),
                                  ),
                                ],
                              ],
                            ),
                          ],
                        ),
                        isThreeLine: true,
                      ),
                    );
                  },
                ),
    );
  }
}   