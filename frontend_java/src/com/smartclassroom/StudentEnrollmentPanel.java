package com.smartclassroom;

import javax.swing.*;
import javax.swing.table.DefaultTableModel;
import java.awt.*;
import java.io.File;
import java.net.URI;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.file.Files;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;

import com.google.gson.JsonArray;
import com.google.gson.JsonObject;

public class StudentEnrollmentPanel extends JPanel {
    private final MainApp mainApp;

    private JTextField rollField;
    private JTextField nameField;
    private JTextField classField;
    private JTextField sectionField;
    private JLabel photoLabel;
    private File selectedPhoto;

    private DefaultTableModel tableModel;
    private JTable studentsTable;
    private final List<Integer> studentIds = new ArrayList<>();

    public StudentEnrollmentPanel(MainApp app) {
        this.mainApp = app;
        setLayout(new BorderLayout());
        setBackground(Color.WHITE);
        initUi();
        loadStudents();
    }

    private void initUi() {
        JLabel title = new JLabel("Student Enrollment");
        title.setFont(new Font("Arial", Font.BOLD, 22));
        title.setBorder(BorderFactory.createEmptyBorder(10, 20, 10, 20));
        add(title, BorderLayout.NORTH);

        JSplitPane split = new JSplitPane(JSplitPane.HORIZONTAL_SPLIT);
        split.setResizeWeight(0.4);

        JPanel form = new JPanel(new GridBagLayout());
        form.setBorder(BorderFactory.createTitledBorder("Register new student"));
        GridBagConstraints gbc = new GridBagConstraints();
        gbc.insets = new Insets(5, 5, 5, 5);
        gbc.fill = GridBagConstraints.HORIZONTAL;

        gbc.gridx = 0; gbc.gridy = 0;
        form.add(new JLabel("Roll number:"), gbc);
        gbc.gridx = 1;
        rollField = new JTextField(15);
        form.add(rollField, gbc);

        gbc.gridx = 0; gbc.gridy = 1;
        form.add(new JLabel("Name:"), gbc);
        gbc.gridx = 1;
        nameField = new JTextField(15);
        form.add(nameField, gbc);

        gbc.gridx = 0; gbc.gridy = 2;
        form.add(new JLabel("Class:"), gbc);
        gbc.gridx = 1;
        classField = new JTextField(15);
        form.add(classField, gbc);

        gbc.gridx = 0; gbc.gridy = 3;
        form.add(new JLabel("Section:"), gbc);
        gbc.gridx = 1;
        sectionField = new JTextField(15);
        form.add(sectionField, gbc);

        gbc.gridx = 0; gbc.gridy = 4;
        form.add(new JLabel("Photo:"), gbc);
        gbc.gridx = 1;
        JButton chooseBtn = new JButton("Choose image");
        chooseBtn.addActionListener(e -> choosePhoto());
        form.add(chooseBtn, gbc);

        gbc.gridx = 0; gbc.gridy = 5; gbc.gridwidth = 2;
        photoLabel = new JLabel("No photo selected", SwingConstants.CENTER);
        photoLabel.setPreferredSize(new Dimension(200, 200));
        photoLabel.setBorder(BorderFactory.createLineBorder(Color.GRAY));
        form.add(photoLabel, gbc);

        gbc.gridx = 0; gbc.gridy = 6; gbc.gridwidth = 1;
        JButton registerBtn = new JButton("Register");
        registerBtn.addActionListener(e -> registerStudent());
        form.add(registerBtn, gbc);

        gbc.gridx = 1;
        JButton clearBtn = new JButton("Clear");
        clearBtn.addActionListener(e -> clearForm());
        form.add(clearBtn, gbc);

        split.setLeftComponent(form);

        // Right side table
        String[] cols = {"Roll", "Name", "Class", "Section", "Registered On"};
        tableModel = new DefaultTableModel(cols, 0) {
            @Override
            public boolean isCellEditable(int row, int column) {
                return false;
            }
        };
        studentsTable = new JTable(tableModel);
        JScrollPane scroll = new JScrollPane(studentsTable);
        scroll.setBorder(BorderFactory.createTitledBorder("Registered students"));

        JPanel right = new JPanel(new BorderLayout());
        right.add(scroll, BorderLayout.CENTER);

        JButton refreshBtn = new JButton("Refresh");
        refreshBtn.addActionListener(e -> loadStudents());
        JButton deleteBtn = new JButton("Delete selected");
        deleteBtn.addActionListener(e -> deleteSelected());
        JPanel bottom = new JPanel(new FlowLayout(FlowLayout.RIGHT));
        bottom.add(deleteBtn);
        bottom.add(refreshBtn);
        right.add(bottom, BorderLayout.SOUTH);

        split.setRightComponent(right);

        add(split, BorderLayout.CENTER);
    }

    private void choosePhoto() {
        JFileChooser chooser = new JFileChooser();
        int result = chooser.showOpenDialog(this);
        if (result == JFileChooser.APPROVE_OPTION) {
            selectedPhoto = chooser.getSelectedFile();
            ImageIcon icon = new ImageIcon(selectedPhoto.getAbsolutePath());
            Image img = icon.getImage().getScaledInstance(200, 200, Image.SCALE_SMOOTH);
            photoLabel.setIcon(new ImageIcon(img));
            photoLabel.setText(null);
        }
    }

    private void registerStudent() {
        if (!validateForm()) {
            return;
        }

        try {
            String boundary = "----SmartClassroomBoundary" + System.currentTimeMillis();
            var body = buildMultipart(boundary);

            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(mainApp.getServerUrl() + "/api/students/register-from-image"))
                    .timeout(Duration.ofSeconds(10))
                    .header("Content-Type", "multipart/form-data; boundary=" + boundary)
                    .POST(HttpRequest.BodyPublishers.ofByteArray(body))
                    .build();

            mainApp.getHttpClient().sendAsync(request, HttpResponse.BodyHandlers.ofString())
                    .thenApply(HttpResponse::body)
                    .thenAccept(resp -> SwingUtilities.invokeLater(() -> handleRegisterResponse(resp)));
        } catch (Exception ex) {
            JOptionPane.showMessageDialog(this, "Error: " + ex.getMessage());
        }
    }

    private boolean validateForm() {
        String roll = rollField.getText().trim();
        String name = nameField.getText().trim();
        String cls = classField.getText().trim();
        String sec = sectionField.getText().trim();

        if (roll.isEmpty() || name.isEmpty() || cls.isEmpty()) {
            JOptionPane.showMessageDialog(this, "Roll number, name and class are required.");
            return false;
        }
        if (!roll.matches("[A-Za-z0-9_-]+")) {
            JOptionPane.showMessageDialog(this, "Roll number can contain only letters, digits, '-' and '_'.");
            return false;
        }
        if (!cls.matches("[A-Za-z0-9 ]+")) {
            JOptionPane.showMessageDialog(this, "Class should contain only letters, digits and spaces.");
            return false;
        }
        if (!sec.isEmpty() && !sec.matches("[A-Za-z0-9]{1,3}")) {
            JOptionPane.showMessageDialog(this, "Section should be 1–3 letters/digits.");
            return false;
        }
        if (selectedPhoto == null) {
            JOptionPane.showMessageDialog(this, "Please choose a photo.");
            return false;
        }
        return true;
    }

    private byte[] buildMultipart(String boundary) throws Exception {
        String nl = "\r\n";
        StringBuilder sb = new StringBuilder();

        sb.append("--").append(boundary).append(nl);
        sb.append("Content-Disposition: form-data; name=\"roll_number\"").append(nl).append(nl);
        sb.append(rollField.getText().trim()).append(nl);

        sb.append("--").append(boundary).append(nl);
        sb.append("Content-Disposition: form-data; name=\"name\"").append(nl).append(nl);
        sb.append(nameField.getText().trim()).append(nl);

        sb.append("--").append(boundary).append(nl);
        sb.append("Content-Disposition: form-data; name=\"class\"").append(nl).append(nl);
        sb.append(classField.getText().trim()).append(nl);

        sb.append("--").append(boundary).append(nl);
        sb.append("Content-Disposition: form-data; name=\"section\"").append(nl).append(nl);
        sb.append(sectionField.getText().trim()).append(nl);

        sb.append("--").append(boundary).append(nl);
        sb.append("Content-Disposition: form-data; name=\"image\"; filename=\"")
                .append(selectedPhoto.getName()).append("\"").append(nl);
        sb.append("Content-Type: image/jpeg").append(nl).append(nl);

        byte[] header = sb.toString().getBytes();
        byte[] fileBytes = Files.readAllBytes(selectedPhoto.toPath());
        byte[] footer = (nl + "--" + boundary + "--" + nl).getBytes();

        byte[] all = new byte[header.length + fileBytes.length + footer.length];
        System.arraycopy(header, 0, all, 0, header.length);
        System.arraycopy(fileBytes, 0, all, header.length, fileBytes.length);
        System.arraycopy(footer, 0, all, header.length + fileBytes.length, footer.length);
        return all;
    }

    private void handleRegisterResponse(String json) {
        try {
            JsonObject obj = mainApp.getGson().fromJson(json, JsonObject.class);
            boolean success = obj.get("success").getAsBoolean();
            String msg = obj.get("message").getAsString();
            JOptionPane.showMessageDialog(this, msg);
            if (success) {
                clearForm();
                loadStudents();
            }
        } catch (Exception e) {
            JOptionPane.showMessageDialog(this, "Unexpected response: " + json);
        }
    }

    private void clearForm() {
        rollField.setText("");
        nameField.setText("");
        classField.setText("");
        sectionField.setText("");
        selectedPhoto = null;
        photoLabel.setIcon(null);
        photoLabel.setText("No photo selected");
    }

    private void loadStudents() {
        try {
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(mainApp.getServerUrl() + "/api/students"))
                    .timeout(Duration.ofSeconds(3))
                    .GET()
                    .build();

            mainApp.getHttpClient().sendAsync(request, HttpResponse.BodyHandlers.ofString())
                    .thenApply(HttpResponse::body)
                    .thenAccept(body -> SwingUtilities.invokeLater(() -> updateTable(body)));
        } catch (Exception ignored) {
        }
    }

    private void updateTable(String json) {
        tableModel.setRowCount(0);
        studentIds.clear();
        try {
            JsonObject root = mainApp.getGson().fromJson(json, JsonObject.class);
            if (!root.has("students")) return;
            JsonArray arr = root.getAsJsonArray("students");
            for (int i = 0; i < arr.size(); i++) {
                JsonObject s = arr.get(i).getAsJsonObject();
                int id = s.get("id").getAsInt();
                studentIds.add(id);
                tableModel.addRow(new Object[]{
                        s.get("roll_number").getAsString(),
                        s.get("name").getAsString(),
                        s.get("class").getAsString(),
                        s.get("section").getAsString(),
                        s.get("registered_on").getAsString()
                });
            }
        } catch (Exception ignored) {
        }
    }

    public void refreshData() {
        loadStudents();
    }

    private void deleteSelected() {
        int row = studentsTable.getSelectedRow();
        if (row < 0) {
            JOptionPane.showMessageDialog(this, "Select a student to delete.");
            return;
        }
        if (row >= studentIds.size()) {
            JOptionPane.showMessageDialog(this, "Internal selection error – please refresh and try again.");
            return;
        }
        int studentId = studentIds.get(row);
        int confirm = JOptionPane.showConfirmDialog(
                this,
                "Delete selected student?",
                "Confirm delete",
                JOptionPane.YES_NO_OPTION
        );
        if (confirm != JOptionPane.YES_OPTION) {
            return;
        }
        try {
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(mainApp.getServerUrl() + "/api/students/" + studentId))
                    .timeout(Duration.ofSeconds(5))
                    .DELETE()
                    .build();
            mainApp.getHttpClient().sendAsync(request, HttpResponse.BodyHandlers.ofString())
                    .thenApply(HttpResponse::body)
                    .thenAccept(body -> SwingUtilities.invokeLater(() -> {
                        try {
                            JsonObject obj = mainApp.getGson().fromJson(body, JsonObject.class);
                            boolean ok = obj.has("success") && obj.get("success").getAsBoolean();
                            if (!ok) {
                                JOptionPane.showMessageDialog(this, "Delete failed: " + body);
                            }
                        } catch (Exception e) {
                            JOptionPane.showMessageDialog(this, "Delete response: " + body);
                        }
                        loadStudents();
                    }));
        } catch (Exception ex) {
            JOptionPane.showMessageDialog(this, "Error deleting: " + ex.getMessage());
        }
    }
}

