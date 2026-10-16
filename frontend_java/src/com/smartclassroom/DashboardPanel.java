package com.smartclassroom;

import javax.imageio.ImageIO;
import javax.swing.*;
import java.awt.*;
import java.awt.image.BufferedImage;
import java.io.ByteArrayInputStream;
import java.net.URI;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;

public class DashboardPanel extends JPanel {
    private final MainApp mainApp;

    private JLabel cameraLabel;
    private JLabel studentsDetectedLabel;
    private JLabel avgAttentionLabel;
    private JLabel fpsLabel;

    private Timer refreshTimer;

    public DashboardPanel(MainApp app) {
        this.mainApp = app;
        setLayout(new BorderLayout());
        setBackground(Color.WHITE);
        initUi();
        startAutoRefresh();
    }

    private void initUi() {
        JPanel top = new JPanel(new BorderLayout());
        top.setBorder(BorderFactory.createEmptyBorder(10, 20, 10, 20));
        JLabel title = new JLabel("Teacher Dashboard");
        title.setFont(new Font("Arial", Font.BOLD, 22));
        top.add(title, BorderLayout.WEST);

        JButton refreshButton = new JButton("Refresh");
        refreshButton.addActionListener(e -> refreshData());
        top.add(refreshButton, BorderLayout.EAST);
        add(top, BorderLayout.NORTH);

        JSplitPane split = new JSplitPane(JSplitPane.HORIZONTAL_SPLIT);
        split.setResizeWeight(0.65);

        JPanel left = new JPanel(new BorderLayout());
        left.setBorder(BorderFactory.createTitledBorder("Live Classroom Feed"));
        cameraLabel = new JLabel("Start camera from backend or Settings", SwingConstants.CENTER);
        cameraLabel.setOpaque(true);
        cameraLabel.setBackground(Color.BLACK);
        cameraLabel.setForeground(Color.WHITE);
        cameraLabel.setPreferredSize(new Dimension(640, 480));
        left.add(new JScrollPane(cameraLabel), BorderLayout.CENTER);
        split.setLeftComponent(left);

        JPanel right = new JPanel();
        right.setLayout(new BoxLayout(right, BoxLayout.Y_AXIS));

        JPanel statsPanel = new JPanel(new GridLayout(4, 2, 5, 5));
        statsPanel.setBorder(BorderFactory.createTitledBorder("Classroom Stats"));

        statsPanel.add(new JLabel("Students detected:"));
        studentsDetectedLabel = new JLabel("0");
        statsPanel.add(studentsDetectedLabel);

        statsPanel.add(new JLabel("Avg attention:"));
        avgAttentionLabel = new JLabel("0%");
        statsPanel.add(avgAttentionLabel);

        statsPanel.add(new JLabel("FPS:"));
        fpsLabel = new JLabel("0");
        statsPanel.add(fpsLabel);

        right.add(statsPanel);

        split.setRightComponent(right);

        add(split, BorderLayout.CENTER);
    }

    private void startAutoRefresh() {
        refreshTimer = new Timer(2000, e -> refreshData());
        refreshTimer.start();
    }

    public void refreshData() {
        fetchStatus();
        fetchFrame();
    }

    private void fetchStatus() {
        try {
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(mainApp.getServerUrl() + "/api/status"))
                    .timeout(Duration.ofSeconds(2))
                    .GET()
                    .build();

            mainApp.getHttpClient().sendAsync(request, HttpResponse.BodyHandlers.ofString())
                    .thenApply(HttpResponse::body)
                    .thenAccept(body -> SwingUtilities.invokeLater(() -> updateStatus(body)));
        } catch (Exception ignored) {
        }
    }

    private void updateStatus(String json) {
        try {
            JsonObject root = mainApp.getGson().fromJson(json, JsonObject.class);
            if (!root.has("classroom_stats")) return;
            JsonObject statsRoot = root.getAsJsonObject("classroom_stats");
            if (!statsRoot.has("camera_0")) return;
            JsonObject stats = statsRoot.getAsJsonObject("camera_0");

            studentsDetectedLabel.setText(stats.get("students_detected").getAsString());
            double avg = stats.get("avg_attention").getAsDouble() * 100.0;
            avgAttentionLabel.setText(String.format("%.1f%%", avg));
            fpsLabel.setText(String.format("%.1f", stats.get("fps").getAsDouble()));
        } catch (Exception ignored) {
        }
    }

    private void fetchFrame() {
        try {
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(mainApp.getServerUrl() + "/api/camera/frame/0"))
                    .timeout(Duration.ofSeconds(2))
                    .GET()
                    .build();

            mainApp.getHttpClient().sendAsync(request, HttpResponse.BodyHandlers.ofByteArray())
                    .thenApply(HttpResponse::body)
                    .thenAccept(bytes -> SwingUtilities.invokeLater(() -> updateFrame(bytes)));
        } catch (Exception ignored) {
        }
    }

    private void updateFrame(byte[] bytes) {
        if (bytes == null || bytes.length == 0) {
            return;
        }
        try {
            ByteArrayInputStream bis = new ByteArrayInputStream(bytes);
            BufferedImage img = ImageIO.read(bis);
            if (img != null) {
                cameraLabel.setIcon(new ImageIcon(img));
                cameraLabel.setText(null);
            }
        } catch (Exception e) {
            cameraLabel.setText("Failed to load frame");
            cameraLabel.setIcon(null);
        }
    }
}

