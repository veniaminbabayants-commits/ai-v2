using System.Net.Http;
using System.Net.Http.Json;
using System.Runtime.InteropServices;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Interop;
using System.Windows.Media;
using System.Windows.Shapes;

namespace BobAiOverlay;

public partial class MainWindow : Window
{
    private static readonly HttpClient Http = new() { Timeout = TimeSpan.FromSeconds(100) };
    private const string ApiBase = "http://127.0.0.1:8765";
    private const int HOTKEY_ID = 9001;
    private const uint MOD_NOREPEAT = 0x4000;
    private const uint VK_F10 = 0x79;
    private HwndSource? _source;
    private bool _busy;
    private string _mode = "server";

    [DllImport("user32.dll", SetLastError = true)]
    private static extern bool RegisterHotKey(IntPtr hWnd, int id, uint fsModifiers, uint vk);
    [DllImport("user32.dll", SetLastError = true)]
    private static extern bool UnregisterHotKey(IntPtr hWnd, int id);
    private const int WM_HOTKEY = 0x0312;

    public MainWindow()
    {
        InitializeComponent();
        AddMessage("TYLER-AI", "Привет! Выбери сервер и категорию либо открой отдельный раздел «Правила проекта». В серверном режиме я не смешиваю материалы разных серверов.", false);
        ServerBox.ItemsSource = new[] { "RED", "YELLOW", "GREEN", "AZURE", "SILVER", "ROSE", "BLACK", "SKY", "TITAN", "FIRE", "LIME", "X" };
        OrganizationBox.ItemsSource = new[] { "Все организации", "Общее", "ППС", "ГИБДД", "Армия", "МЧС", "Правительство", "Администрация" };
        SphereBox.ItemsSource = new[] { "Все категории", "Гос. организации", "Криминал", "ТРК", "Информация сервера" };
        ServerBox.SelectedIndex = 0;
        OrganizationBox.SelectedIndex = 0;
        SphereBox.SelectedIndex = 0;
    }

    private async void Window_Loaded(object sender, RoutedEventArgs e)
    {
        var handle = new WindowInteropHelper(this).Handle;
        _source = HwndSource.FromHwnd(handle);
        _source?.AddHook(HwndHook);
        bool registered = RegisterHotKey(handle, HOTKEY_ID, MOD_NOREPEAT, VK_F10);
        StatusText.Text = registered ? "Готово · F10 — показать/скрыть" : "Готово · не удалось зарегистрировать F10";
        try
        {
            var response = await Http.GetAsync($"{ApiBase}/health");
            if (response.IsSuccessStatusCode)
                StatusText.Text = "API подключён · F10 — показать/скрыть";
            else
                StatusText.Text = "API отвечает с ошибкой";
        }
        catch
        {
            StatusText.Text = "Backend не запущен · см. README";
        }
    }

    private IntPtr HwndHook(IntPtr hwnd, int msg, IntPtr wParam, IntPtr lParam, ref bool handled)
    {
        if (msg == WM_HOTKEY && wParam.ToInt32() == HOTKEY_ID)
        {
            if (IsVisible)
            {
                Hide();
            }
            else
            {
                Show();
                WindowState = WindowState.Normal;
                Activate();
                QuestionBox.Focus();
            }
            handled = true;
        }
        return IntPtr.Zero;
    }

    private void Window_Closing(object? sender, System.ComponentModel.CancelEventArgs e)
    {
        var handle = new WindowInteropHelper(this).Handle;
        UnregisterHotKey(handle, HOTKEY_ID);
        _source?.RemoveHook(HwndHook);
    }

    private async void Send_Click(object sender, RoutedEventArgs e) => await SendQuestionAsync();

    private async void QuestionBox_KeyDown(object sender, KeyEventArgs e)
    {
        if (e.Key == Key.Enter && Keyboard.Modifiers == ModifierKeys.None)
        {
            e.Handled = true;
            await SendQuestionAsync();
        }
    }

    private async Task SendQuestionAsync()
    {
        if (_busy) return;
        var question = QuestionBox.Text.Trim();
        if (question.Length == 0) return;
        QuestionBox.Clear();
        AddMessage("Вы", question, true);
        _busy = true;
        StatusText.Text = "Ищу материалы и формирую ответ…";
        var waiting = AddMessage("TYLER-AI", "Думаю…", false);
        try
        {
            using var response = await Http.PostAsJsonAsync($"{ApiBase}/chat", new {
                message = question,
                mode = _mode,
                server = ServerBox.SelectedItem?.ToString() ?? "RED",
                organization = OrganizationBox.SelectedItem?.ToString() ?? "Все организации",
                sphere = SphereBox.SelectedItem?.ToString() ?? "Все категории"
            });
            var json = await response.Content.ReadAsStringAsync();
            if (!response.IsSuccessStatusCode)
            {
                string detail = TryGetDetail(json) ?? $"Ошибка сервера ({(int)response.StatusCode}).";
                waiting.Text = detail;
                StatusText.Text = "Ошибка запроса";
            }
            else
            {
                using var doc = JsonDocument.Parse(json);
                var answer = doc.RootElement.TryGetProperty("answer", out var a) ? a.GetString() : "Пустой ответ.";
                waiting.Text = answer ?? "Пустой ответ.";
                StatusText.Text = "Готово · проверь первоисточники";
            }
        }
        catch (Exception ex)
        {
            waiting.Text = "Не удалось подключиться к backend. Проверь, что сервер запущен на 127.0.0.1:8765.\n\n" + ex.Message;
            StatusText.Text = "Нет подключения";
        }
        finally
        {
            _busy = false;
            ChatScroll.ScrollToEnd();
        }
    }

    private static string? TryGetDetail(string json)
    {
        try
        {
            using var doc = JsonDocument.Parse(json);
            return doc.RootElement.TryGetProperty("detail", out var detail) ? detail.GetString() : null;
        }
        catch { return null; }
    }

    private TextBox AddMessage(string who, string text, bool isUser)
    {
        var outer = new Border
        {
            Background = new SolidColorBrush((Color)ColorConverter.ConvertFromString(isUser ? "#FF172B2A" : "#FF151E26")),
            CornerRadius = new CornerRadius(12),
            Padding = new Thickness(12),
            Margin = new Thickness(0, 0, 0, 10),
            HorizontalAlignment = HorizontalAlignment.Stretch
        };
        var stack = new StackPanel();
        stack.Children.Add(new TextBlock
        {
            Text = who,
            Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString(isUser ? "#FF83E3C9" : "#FF6ED7C2")),
            FontWeight = FontWeights.SemiBold,
            FontSize = 11,
            Margin = new Thickness(0, 0, 0, 5)
        });
        // Read-only TextBox allows selecting and copying message text.
        var body = new TextBox
        {
            Text = text,
            IsReadOnly = true,
            IsReadOnlyCaretVisible = true,
            AcceptsReturn = true,
            TextWrapping = TextWrapping.Wrap,
            Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#FFE9F0F4")),
            Background = Brushes.Transparent,
            BorderThickness = new Thickness(0),
            Padding = new Thickness(0),
            FontSize = 13,
            IsTabStop = true,
            IsHitTestVisible = true,
            Focusable = true,
            MinHeight = 20,
            HorizontalScrollBarVisibility = ScrollBarVisibility.Disabled,
            VerticalScrollBarVisibility = ScrollBarVisibility.Disabled
        };
        stack.Children.Add(body);
        outer.Child = stack;
        Messages.Children.Add(outer);
        ChatScroll.ScrollToEnd();
        return body;
    }

    private void Header_MouseLeftButtonDown(object sender, MouseButtonEventArgs e)
    {
        if (e.ChangedButton == MouseButton.Left && e.ButtonState == MouseButtonState.Pressed)
        {
            try
            {
                DragMove();
            }
            catch (InvalidOperationException)
            {
                // Перетаскивание могло завершиться раньше времени.
            }
        }
    }

    private void ServerMode_Click(object sender, RoutedEventArgs e)
    {
        _mode = "server";
        ServerBox.IsEnabled = true;
        OrganizationBox.IsEnabled = true;
        SphereBox.IsEnabled = true;
        ServerBox.Visibility = Visibility.Visible;
        OrganizationBox.Visibility = Visibility.Visible;
        SphereBox.Visibility = Visibility.Visible;
        ServerLabel.Visibility = Visibility.Visible;
        OrganizationLabel.Visibility = Visibility.Visible;
        SphereLabel.Visibility = Visibility.Visible;
        RulesHint.Visibility = Visibility.Collapsed;
        ModeStatus.Text = "Режим: выбранный сервер";
        StatusText.Text = "Вопросы ищутся только в материалах выбранного сервера";
    }

    private void RulesMode_Click(object sender, RoutedEventArgs e)
    {
        _mode = "rules";
        ServerBox.IsEnabled = false;
        OrganizationBox.IsEnabled = false;
        SphereBox.IsEnabled = false;
        ServerBox.Visibility = Visibility.Collapsed;
        OrganizationBox.Visibility = Visibility.Collapsed;
        SphereBox.Visibility = Visibility.Collapsed;
        ServerLabel.Visibility = Visibility.Collapsed;
        OrganizationLabel.Visibility = Visibility.Collapsed;
        SphereLabel.Visibility = Visibility.Collapsed;
        RulesHint.Visibility = Visibility.Visible;
        ModeStatus.Text = "Режим: общие правила проекта";
        StatusText.Text = "Ищу только глобальные правила проекта";
    }

    private void Minimize_Click(object sender, RoutedEventArgs e) => WindowState = WindowState.Minimized;
    private void Close_Click(object sender, RoutedEventArgs e) => Hide();
}
