package com.smartclassroom;

import javax.swing.*;
import java.awt.*;
import java.io.FileInputStream;
import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpClient.Version;
import java.net.http.HttpResponse;
import java.net.http.HttpRequest;
import java.time.Duration;
import java.util.Properties;

import com.google.gson.Gson;

public class MainApp extends JFrame {
    private CardLayout cardLayout;
    private JPanel mainPanel;

    private DashboardPanel dashboardPanel;
    private StudentEnrollmentPanel enrollmentPanel;

    private HttpClient httpClient;
    private Gson gson;
    private String serverUrl = "http://localhost:5000";

    public MainApp() {
        initHttp();
        initUi();
        loadConfig();
    }

    private void initHttp() {
        httpClient = HttpClient.newBuilder()
                .version(Version.HTTP_1_1)
                .connectTimeout(Duration.ofSeconds(5))
                .build();
        gson = new Gson();
    }

    private void initUi() {
        setTitle("Smart Classroom - Edge AI Education System");
        setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
        setLayout(new BorderLayout());

        // Sidebar
        JPanel sidebar = new JPanel();
        sidebar.setBackground(new Color(33, 33, 33));
        sidebar.setPreferredSize(new Dimension(200, 600));
        sidebar.setLayout(new BoxLayout(sidebar, BoxLayout.Y_AXIS));

        JLabel title = new JLabel("Smart Classroom");
        title.setForeground(Color.WHITE);
        title.setFont(new Font("Arial", Font.BOLD, 18));
        title.setAlignmentX(Component.CENTER_ALIGNMENT);
        title.setBorder(BorderFactory.createEmptyBorder(20, 10, 20, 10));
        sidebar.add(title);

        JButton dashBtn = createNavButton("Dashboard", () -> showDashboard());
        JButton enrollBtn = createNavButton("Student Enrollment", () -> showEnrollment());
        sidebar.add(dashBtn);
        sidebar.add(enrollBtn);

        sidebar.add(Box.createVerticalGlue());

        JLabel statusLabel = new JLabel("Backend: " + serverUrl);
        statusLabel.setForeground(Color.LIGHT_GRAY);
        statusLabel.setAlignmentX(Component.CENTER_ALIGNMENT);
        sidebar.add(statusLabel);

        // Main content
        cardLayout = new CardLayout();
        mainPanel = new JPanel(cardLayout);

        dashboardPanel = new DashboardPanel(this);
        enrollmentPanel = new StudentEnrollmentPanel(this);

        mainPanel.add(dashboardPanel, "DASHBOARD");
        mainPanel.add(enrollmentPanel, "ENROLLMENT");

        add(sidebar, BorderLayout.WEST);
        add(mainPanel, BorderLayout.CENTER);

        setSize(1100, 700);
        setLocationRelativeTo(null);

        showDashboard();
    }

    private JButton createNavButton(String text, Runnable action) {
        JButton button = new JButton(text);
        button.setForeground(Color.WHITE);
        button.setBackground(new Color(33, 33, 33));
        button.setBorderPainted(false);
        button.setFocusPainted(false);
        button.setAlignmentX(Component.CENTER_ALIGNMENT);
        button.setMaximumSize(new Dimension(180, 40));
        button.addActionListener(e -> action.run());
        return button;
    }

    private void loadConfig() {
        try {
            Properties props = new Properties();
            props.load(new FileInputStream("config.properties"));
            serverUrl = props.getProperty("server.url", serverUrl);
        } catch (IOException ignored) {
        }
    }

    public HttpClient getHttpClient() {
        return httpClient;
    }

    public Gson getGson() {
        return gson;
    }

    public String getServerUrl() {
        return serverUrl;
    }

    public void showDashboard() {
        cardLayout.show(mainPanel, "DASHBOARD");
        dashboardPanel.refreshData();
    }

    public void showEnrollment() {
        cardLayout.show(mainPanel, "ENROLLMENT");
        enrollmentPanel.refreshData();
    }

    public static void main(String[] args) {
        try {
            UIManager.setLookAndFeel(UIManager.getSystemLookAndFeelClassName());
        } catch (Exception ignored) {
        }

        SwingUtilities.invokeLater(() -> {
            new MainApp().setVisible(true);
        });
    }
}

