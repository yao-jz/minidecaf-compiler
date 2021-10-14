int fib(int n) {
    if(n == 0) {
		return 0;
	}
	return fib(n-1);
	
}

int main() {
    int n = 5;
    return fib(n);
}