int C[2][10000];
int P = 10000007;

int main() {
    int n = 5996;

    C[0][0] = 1;
    int b = 0;
    for (int i = 1; i <= n; i = i + 1) {
        for (int j = 0; j <= i; j = j + 1)
            C[1 - b][j] = !j ? 1 : (C[b][j] + C[b][j - 1]) % P;
        b = 1 - b;
    }

    return 0;
}
